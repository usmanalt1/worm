"""Turn mart_team_schedule_load into home-minus-away model features."""

import pandas as pd

from services.ml_model.features.transformer_base import TransformerBase
from config.logger import get_logger

LOAD_COLS = ["travel_km", "tz_delta", "altitude_gain", "games_prev_7d", "road_trip_game"]


class ScheduleLoadTransformer(TransformerBase):
    def __init__(self, model_df: pd.DataFrame, df_schedule_load: pd.DataFrame):
        self.model_df = model_df
        self.df_schedule_load = df_schedule_load
        self.logger = get_logger(__name__)

    def transform(self) -> pd.DataFrame:
        self.logger.info("Transform Apply Schedule Load...")
        try:
            model_df = self._merge_differentials()
            self.logger.info("Transform Apply Schedule Load Done...")
        except Exception as e:
            self.logger.error(f"Error in transforming schedule load: {e}")
            raise

        return model_df

    def _merge_differentials(self) -> pd.DataFrame:
        # The mart already carries is_home, so the sides come straight off it.
        load = self.df_schedule_load.drop_duplicates(subset=["game_id", "team_id"])
        home = load[load["is_home"] == 1].set_index("game_id")[LOAD_COLS]
        away = load[load["is_home"] == 0].set_index("game_id")[LOAD_COLS]

        diffs = (home - away).reset_index()
        diffs = diffs.rename(columns={c: f"diff_{c}" for c in LOAD_COLS})

        model_df = self.model_df.merge(diffs, on="game_id", how="left")

        diff_cols = [f"diff_{c}" for c in LOAD_COLS]
        before = len(model_df)
        model_df = model_df.dropna(subset=diff_cols).reset_index(drop=True)
        self.logger.info(
            f"dropped {before - len(model_df)} rows with no schedule load, {len(model_df)} remain"
        )

        return model_df
