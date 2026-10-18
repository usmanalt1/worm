"""Rate each team's roster from its players' recent value, so a signing counts before
the team has played a game with it."""

import pandas as pd

from services.ml_model.features.transformer_base import TransformerBase
from config.logger import get_logger

# A 23-man sum rewards depth that never plays; eight is about a playing rotation.
ROTATION_SIZE = 8
# Five players for 48 minutes, so the weighted sum is denominated in one team's game.
TEAM_MINUTES = 240.0

VALUE_COLS = ["player_id", "game_date", "value_pre", "minutes_pre"]
ROSTER_COLS = ["game_id", "team_id", "game_date", "player_id"]


class RosterValueTransformer(TransformerBase):
    def __init__(
        self,
        model_df: pd.DataFrame,
        df_player_value: pd.DataFrame,
        df_roster_history: pd.DataFrame,
        df_current_roster: pd.DataFrame,
        df_games: pd.DataFrame,
    ):
        self.model_df = model_df
        self.df_player_value = df_player_value
        self.df_roster_history = df_roster_history
        self.df_current_roster = df_current_roster
        self.df_games = df_games
        self.logger = get_logger(__name__)

    def transform(self) -> pd.DataFrame:
        self.logger.info("Transform Apply Roster Value...")
        try:
            team_schedule = self._team_schedule()
            rosters = pd.concat(
                [self._historical_rosters(team_schedule), self._upcoming_rosters(team_schedule)],
                ignore_index=True,
            )
            rated = self._attach_player_value(rosters)
            model_df = self._merge_differentials(self._team_value(rated), team_schedule)

            self.logger.info("Transform Apply Roster Value Done...")
        except Exception as e:
            self.logger.error(f"Error in transforming roster value: {e}")
            raise

        return model_df

    def _team_schedule(self) -> pd.DataFrame:
        """One row per team per game, including games with no result yet."""
        cols = ["game_id", "game_date", "season", "home_team_id", "away_team_id", "home_wl"]
        games = self.df_games[cols].drop_duplicates()
        games = games.assign(game_date=pd.to_datetime(games["game_date"])).dropna(subset=["game_date"])
        games["is_played"] = games["home_wl"].notna()

        kept = ["game_id", "game_date", "season", "team_id", "is_played"]
        home = games.rename(columns={"home_team_id": "team_id"})[kept]
        away = games.rename(columns={"away_team_id": "team_id"})[kept]

        return pd.concat([home.assign(is_home=1), away.assign(is_home=0)], ignore_index=True)

    def _historical_rosters(self, team_schedule: pd.DataFrame) -> pd.DataFrame:
        """Who was on each team when a played game was played.

        Deliberately the roster rather than the box score: who actually took the court
        encodes that night's injuries and rest, which is not known before tip-off, and
        would train the model on information a live prediction never has.
        """
        played = team_schedule[team_schedule["is_played"]]
        windows = self.df_roster_history[
            ["season", "team_id", "player_id", "first_game_with_team", "last_game_with_team"]
        ].copy()
        for col in ("first_game_with_team", "last_game_with_team"):
            windows[col] = pd.to_datetime(windows[col])

        candidates = played.merge(windows, on=["season", "team_id"], how="inner")
        on_roster = candidates["game_date"].between(
            candidates["first_game_with_team"], candidates["last_game_with_team"]
        )

        return candidates.loc[on_roster, ROSTER_COLS]

    def _upcoming_rosters(self, team_schedule: pd.DataFrame) -> pd.DataFrame:
        """Today's roster, for games with no result yet.

        teams_roster is a present-day snapshot, so it is only ever applied to games that
        have not happened - using it for a past game would put later signings into it.
        """
        upcoming = team_schedule[~team_schedule["is_played"]]
        roster = self._latest_snapshot_per_player()

        return upcoming.merge(roster, on=["season", "team_id"], how="inner")[ROSTER_COLS]

    def _latest_snapshot_per_player(self) -> pd.DataFrame:
        """Resolve each player to the team they were last snapshotted on.

        teams_roster is keyed on (team_id, player_id, season_id), so a player who changes
        team mid-season gains a row instead of moving: both the old team and the new one
        keep a row, and summing straight off the table counts them twice.
        """
        roster = self.df_current_roster[["season", "team_id", "player_id", "run_timestamp"]]
        latest = roster.sort_values("run_timestamp").drop_duplicates(
            subset=["season", "player_id"], keep="last"
        )

        dropped = len(roster) - len(latest)
        self.logger.info(f"dropped {dropped} superseded roster rows, {len(latest)} remain")

        return latest[["season", "team_id", "player_id"]]

    def _attach_player_value(self, rosters: pd.DataFrame) -> pd.DataFrame:
        """Each roster slot's value as last known before that game."""
        value = self.df_player_value[VALUE_COLS].copy()
        value["game_date"] = pd.to_datetime(value["game_date"])
        value = value.dropna(subset=["game_date", "value_pre", "minutes_pre"])

        rated = pd.merge_asof(
            rosters.sort_values("game_date"),
            value.sort_values("game_date"),
            on="game_date",
            by="player_id",
            direction="backward",
            # Strictly earlier, so a game never reads a value dated the day it is played.
            allow_exact_matches=False,
        )

        unrated = int(rated["value_pre"].isna().sum())
        self.logger.info(f"{len(rated) - unrated} of {len(rated)} roster slots carry a player value")

        return rated.dropna(subset=["value_pre", "minutes_pre"])

    @staticmethod
    def _team_value(rated: pd.DataFrame) -> pd.DataFrame:
        """Minutes-weighted value of each team's rotation for a game.

        Weighted rather than summed because three stars sharing one minutes pool do not
        produce three stars' worth of basketball.
        """
        ranked = rated.sort_values(["game_id", "team_id", "minutes_pre"], ascending=[True, True, False])
        rotation = ranked.groupby(["game_id", "team_id"], sort=False).head(ROTATION_SIZE)

        team_value = (
            rotation.assign(weighted=rotation["value_pre"] * rotation["minutes_pre"])
            .groupby(["game_id", "team_id"], as_index=False)["weighted"]
            .sum()
        )
        team_value["roster_value"] = team_value["weighted"] / TEAM_MINUTES

        return team_value[["game_id", "team_id", "roster_value"]]

    def _merge_differentials(self, team_value: pd.DataFrame, team_schedule: pd.DataFrame) -> pd.DataFrame:
        rated = team_schedule.merge(team_value, on=["game_id", "team_id"], how="left")

        home = rated[rated.is_home == 1].drop_duplicates("game_id").set_index("game_id")["roster_value"]
        away = rated[rated.is_home == 0].drop_duplicates("game_id").set_index("game_id")["roster_value"]

        diffs = (home - away).reset_index().rename(columns={"roster_value": "diff_roster_value"})
        model_df = self.model_df.merge(diffs, on="game_id", how="left")

        # 0 is "no roster edge either way". Dropping instead would delete training games
        # that the box-score and Elo features cover perfectly well.
        missing = int(model_df["diff_roster_value"].isna().sum())
        model_df["diff_roster_value"] = model_df["diff_roster_value"].fillna(0)
        self.logger.info(f"{missing} of {len(model_df)} rows have no roster value, filled with 0")

        return model_df
