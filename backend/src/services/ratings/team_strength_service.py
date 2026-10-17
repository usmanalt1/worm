"""Team strength from game results: Elo ratings and opponent-adjusted margin.

A rating moves only by how far a result beat what the rating already predicted, so
beating a strong team is worth more than beating a weak one. Opponent-adjusted margin
restates each result in points, credited for how good the opponent was at the time.

Both are derived from completed games and known before tip-off, so neither needs roster
or injury information.
"""

import pandas as pd
from sqlalchemy import text

from config.logger import get_logger
from services.ratings.team_strength_constants import (
    CARRYOVER, ELO_PER_POINT, FORM_GAMES, GRAIN, HOME_ADVANTAGE, K, MIN_FORM_GAMES,
    MOV_DAMPING, MOV_DAMPING_PER_ELO, MOV_EXPONENT, MOV_OFFSET, SCALE, START,
    TARGET_SCHEMA, TARGET_TABLE, WRITE_CHUNK_ROWS, ZERO_SUM_TOLERANCE,
)


class TeamStrengthService:
    """Build team Elo ratings and rolling opponent-adjusted margin from dim_games."""

    def __init__(self, engine):
        self.engine = engine
        self.logger = get_logger(__name__)

    def build(self) -> pd.DataFrame:
        """One row per team per game, with its pre-game rating and form."""
        games = self._read_games()
        self.logger.info(f"Rating {len(games)} completed games")
        rated = self._add_form_adjusted_margin(self._accumulate(games))

        problems = self.grain_problems(rated)
        if problems:
            raise ValueError(f"team strength build is unsound: {'; '.join(problems)}")

        return rated

    def write(self, rated: pd.DataFrame) -> int:
        """Replace the mart with this set of ratings.

        Loads a staging table and renames it inside one transaction, so readers keep
        seeing the previous ratings until the new set is complete.
        """
        staging_table = f"{TARGET_TABLE}__staging"

        with self.engine.begin() as connection:
            connection.execute(text(f'drop table if exists "{TARGET_SCHEMA}"."{staging_table}"'))
            rated.to_sql(
                staging_table, connection, schema=TARGET_SCHEMA, if_exists="fail",
                index=False, chunksize=WRITE_CHUNK_ROWS, method="multi",
            )
            connection.execute(text(f'drop table if exists "{TARGET_SCHEMA}"."{TARGET_TABLE}"'))
            connection.execute(
                text(f'alter table "{TARGET_SCHEMA}"."{staging_table}" rename to "{TARGET_TABLE}"')
            )

        self.logger.info(f"Wrote {len(rated)} rows to {TARGET_SCHEMA}.{TARGET_TABLE}")

        return len(rated)

    @staticmethod
    def to_game_features(rated: pd.DataFrame) -> pd.DataFrame:
        """Home-minus-away differentials, one row per game. What the model consumes.

        Takes a built frame rather than building one, so a caller that needs both the
        table and the features does not rate every game twice.
        """
        home = rated[rated.is_home == 1][["game_id", "elo_pre", "form_adj_margin"]]
        away = rated[rated.is_home == 0][["game_id", "elo_pre", "form_adj_margin"]]

        merged = home.merge(away, on="game_id", suffixes=("_home", "_away"))
        merged["diff_team_elo"] = merged.elo_pre_home - merged.elo_pre_away
        merged["diff_adj_margin"] = merged.form_adj_margin_home - merged.form_adj_margin_away

        return merged[["game_id", "diff_team_elo", "diff_adj_margin"]]

    @staticmethod
    def expected_win(edge: float) -> float:
        """Win probability implied by a rating edge, including home advantage."""
        return 1.0 / (1.0 + 10 ** (-edge / SCALE))

    @staticmethod
    def move_size(margin: float, edge: float) -> float:
        """How far one game shifts a rating."""
        return (
            K * (abs(margin) + MOV_OFFSET) ** MOV_EXPONENT
            / (MOV_DAMPING + MOV_DAMPING_PER_ELO * abs(edge))
        )

    @staticmethod
    def carry_into_new_season(rating: float) -> float:
        return START + CARRYOVER * (rating - START)

    @staticmethod
    def grain_problems(rated: pd.DataFrame) -> list:
        """Reasons this rating set must not be published, empty if it is sound."""
        if rated.empty:
            return ["no rows to publish"]

        problems = []

        duplicates = int(rated.duplicated(subset=GRAIN).sum())
        if duplicates:
            problems.append(f"{duplicates} rows duplicate the grain {tuple(GRAIN)}")

        for column in ("elo_pre", "elo_post", "adj_margin"):
            missing = int(rated[column].isna().sum())
            if missing:
                problems.append(f"{column} is null in {missing} rows")

        totals = rated.groupby("game_id")[["elo_pre", "elo_post"]].sum()
        drift = (totals["elo_post"] - totals["elo_pre"]).abs().max()
        if drift > ZERO_SUM_TOLERANCE:
            problems.append(f"elo changes do not cancel within a game (max drift {drift:.2e})")

        return problems

    def _read_games(self) -> pd.DataFrame:
        """Completed regular-season and playoff games, oldest first. Order drives the walk.

        Playoffs carry the same `season`, so a rating runs on into the postseason without
        the new-season regression; only the next regular season regresses it.
        """
        return pd.read_sql(
            """
            select game_id, game_date, season, home_team_id, away_team_id, home_pts, away_pts
            from nba_marts.dim_games
            where season_type in ('regular', 'playoffs')
              and home_wl is not null
              and home_pts is not null
              and away_pts is not null
            order by game_date, game_id
            """,
            self.engine,
        )

    def _rating_entering(self, ratings: dict, seasons: dict, team_id: int, season: str) -> float:
        """A team's rating going into this game, regressed if a new season has started."""
        rating = ratings.get(team_id, START)
        if seasons.get(team_id, season) != season:
            rating = self.carry_into_new_season(rating)

        ratings[team_id] = rating
        seasons[team_id] = season

        return rating

    def _accumulate(self, games: pd.DataFrame) -> pd.DataFrame:
        """Walk games in order, recording each team's rating before and after each one."""
        ratings, seasons = {}, {}
        rows = []

        for game in games.itertuples(index=False):
            home_elo = self._rating_entering(ratings, seasons, game.home_team_id, game.season)
            away_elo = self._rating_entering(ratings, seasons, game.away_team_id, game.season)

            margin = game.home_pts - game.away_pts
            edge = home_elo - away_elo + HOME_ADVANTAGE
            change = self.move_size(margin, edge) * (float(margin > 0) - self.expected_win(edge))

            ratings[game.home_team_id] = home_elo + change
            ratings[game.away_team_id] = away_elo - change

            for team_id, own_elo, opponent_elo, own_margin, is_home in (
                (game.home_team_id, home_elo, away_elo, margin, 1),
                (game.away_team_id, away_elo, home_elo, -margin, 0),
            ):
                rows.append({
                    "season": game.season,
                    "game_id": game.game_id,
                    "game_date": game.game_date,
                    "team_id": team_id,
                    "is_home": is_home,
                    # Before the update, so a game's own result is never inside it.
                    "elo_pre": own_elo,
                    "elo_post": ratings[team_id],
                    "opponent_elo_pre": opponent_elo,
                    "margin": own_margin,
                    "adj_margin": own_margin + (opponent_elo - START) / ELO_PER_POINT,
                })

        return pd.DataFrame(rows)

    def _add_form_adjusted_margin(self, rated: pd.DataFrame) -> pd.DataFrame:
        """Mean adjusted margin over the previous FORM_GAMES games of the season."""
        rated = rated.sort_values(["team_id", "season", "game_date", "game_id"])
        # shift(1) so a game never sees its own result, then re-group for the window
        previous = rated.groupby(["team_id", "season"])["adj_margin"].shift(1)
        rated["form_adj_margin"] = (
            previous.groupby([rated["team_id"], rated["season"]])
            .rolling(FORM_GAMES, min_periods=MIN_FORM_GAMES).mean()
            .reset_index(level=[0, 1], drop=True)
        )
        # Unshifted, so it includes this game: the form a *later* game inherits.
        rated["form_adj_margin_post"] = (
            rated.groupby(["team_id", "season"])["adj_margin"]
            .rolling(FORM_GAMES, min_periods=MIN_FORM_GAMES).mean()
            .reset_index(level=[0, 1], drop=True)
        )

        return rated.reset_index(drop=True)
