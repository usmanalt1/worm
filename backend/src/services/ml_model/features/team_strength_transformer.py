"""Turn mart_team_strength into home-minus-away model features."""

import pandas as pd

from services.ml_model.features.transformer_base import TransformerBase
from services.ratings.team_strength_service import TeamStrengthService
from config.logger import get_logger

RATING_COLS = ["elo_pre", "form_adj_margin"]
# The same strengths once the rated game is counted, which is what a later game inherits.
CARRIED_COLS = ["elo_post", "form_adj_margin_post"]


class TeamStrengthTransformer(TransformerBase):
    def __init__(self, model_df: pd.DataFrame, df_team_strength: pd.DataFrame, df_games: pd.DataFrame):
        self.model_df = model_df
        self.df_team_strength = df_team_strength
        self.df_games = df_games
        self.logger = get_logger(__name__)

    def transform(self) -> pd.DataFrame:
        self.logger.info("Transform Apply Team Strength...")
        try:
            ratings = self._latest_rating_per_team_game()
            model_df = self._merge_differentials(ratings)
            self.logger.info("Transform Apply Team Strength Done...")
        except Exception as e:
            self.logger.error(f"Error in transforming team strength: {e}")
            raise

        return model_df

    def _team_schedule(self) -> pd.DataFrame:
        """One row per team per game, including games with no result yet."""
        cols = ["game_id", "game_date", "season", "home_team_id", "away_team_id"]
        games = self.df_games[cols].drop_duplicates()
        games = games.assign(game_date=pd.to_datetime(games["game_date"])).dropna(subset=["game_date"])

        kept = ["game_id", "game_date", "season", "team_id"]
        home = games.rename(columns={"home_team_id": "team_id"})[kept]
        away = games.rename(columns={"away_team_id": "team_id"})[kept]

        return pd.concat([home.assign(is_home=1), away.assign(is_home=0)], ignore_index=True)

    def _latest_rating_per_team_game(self) -> pd.DataFrame:
        """Each team's strength as it is known before each game it appears in.

        A rated game reads its own pre-game row. A game mart_team_strength does not cover
        - one being predicted - inherits the team's strength after its last rated game,
        regressed to the mean if that game belongs to an earlier season.
        """
        ratings = self.df_team_strength.copy()
        ratings["game_date"] = pd.to_datetime(ratings["game_date"])
        ratings = ratings.dropna(subset=["game_date"])

        own = self._team_schedule().merge(
            ratings[["game_id", "team_id"] + RATING_COLS], on=["game_id", "team_id"], how="left",
        )
        carried = pd.merge_asof(
            own.sort_values("game_date"),
            (
                ratings[["game_date", "team_id", "season"] + CARRIED_COLS]
                .rename(columns={"season": "rated_season"})
                .sort_values("game_date")
            ),
            on="game_date", by="team_id", direction="backward",
        )

        # Elo spans seasons once regressed; form is a within-season window, so last
        # season's says nothing about this one.
        new_season = carried["rated_season"].notna() & (carried["rated_season"] != carried["season"])
        carried["elo_post"] = carried["elo_post"].mask(
            new_season, TeamStrengthService.carry_into_new_season(carried["elo_post"]),
        )
        carried["form_adj_margin_post"] = carried["form_adj_margin_post"].mask(new_season)

        # Keyed on whether the game is rated at all, never on a null feature: a rated
        # game's own as-of match is itself, so filling its missing form from _post would
        # let the game's result into its own features.
        is_rated = carried["elo_pre"].notna()
        for pre, carried_col in zip(RATING_COLS, CARRIED_COLS):
            carried[pre] = carried[pre].where(is_rated, carried[carried_col])

        inherited = carried["elo_pre"].notna().sum() - own["elo_pre"].notna().sum()
        self.logger.info(f"{inherited} team-games inherited a carried rating")

        return carried.drop(columns=CARRIED_COLS + ["rated_season"])

    def _merge_differentials(self, ratings: pd.DataFrame) -> pd.DataFrame:
        home = ratings[ratings.is_home == 1].set_index("game_id")[RATING_COLS]
        away = ratings[ratings.is_home == 0].set_index("game_id")[RATING_COLS]

        diffs = (home - away).reset_index().rename(columns={
            "elo_pre": "diff_team_elo",
            "form_adj_margin": "diff_adj_margin",
        })

        model_df = self.model_df.merge(diffs, on="game_id", how="left")

        # A team's first MIN_FORM_GAMES have no form yet; 0 is "no form edge either way",
        # not a reason to drop a game elo already covers.
        no_form = int(model_df["diff_adj_margin"].isna().sum())
        model_df["diff_adj_margin"] = model_df["diff_adj_margin"].fillna(0)

        before = len(model_df)
        model_df = model_df.dropna(subset=["diff_team_elo"]).reset_index(drop=True)
        self.logger.info(
            f"dropped {before - len(model_df)} rows with no team strength coverage, "
            f"kept {no_form} with no form yet, {len(model_df)} remain"
        )

        return model_df
