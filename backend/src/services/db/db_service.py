from logging import getLogger
from pathlib import Path
from app.models import SeasonRecord, TeamInfo, PlayerInfo, TeamRoster, TeamStats, PlayerStats, TeamMatchups, PlayerAwards, GameSchedule, DraftHistory, PlayerInjury, DimGames, FctTeamStats, FctPlayerStats, DimRosters, DimTeams, AdvancedPlayerSeasonStats, AdvancedTeamSeasonStats, MartTeamStrength, MartTeamScheduleLoad, MartPlayerValue
from django.db import connections
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import os
from services.db.models_upsert import TableModelFactory
from services.interface import StorageBase
from services.object_storage.service import ObjectStorageService
import pandas as pd
from config.settings import settings

logger = getLogger(__name__)

class DBService(StorageBase):
    def __init__(self):
        self.table_model_map = {
            "season_record": SeasonRecord,
            "teams_info": TeamInfo,
            "players_info": PlayerInfo,
            "teams_roster": TeamRoster,
            "team_stats": TeamStats,
            "player_stats": PlayerStats,
            "team_matchups": TeamMatchups,
            "player_awards": PlayerAwards,
            "game_schedule": GameSchedule,
            "draft_history": DraftHistory,
            "player_injuries": PlayerInjury,
            "advanced_player_season_stats": AdvancedPlayerSeasonStats,
            "advanced_team_season_stats": AdvancedTeamSeasonStats,
            "dim_games": DimGames,
            "fct_team_stats": FctTeamStats,
            "fct_player_stats": FctPlayerStats,
            "dim_rosters": DimRosters,
            "dim_teams": DimTeams,
            "mart_team_strength": MartTeamStrength,
            "mart_team_schedule_load": MartTeamScheduleLoad,
            "mart_player_value": MartPlayerValue,
        }
        self.engine = self._engine_from_django()
        self.file_path_parent_name = os.getenv("FILE_PATH_PARENT_NAME")

    @staticmethod
    def _engine_from_django():
        """SQLAlchemy engine onto whatever database Django is configured with, so the
        pandas readers and the ORM can never address different databases."""
        config = connections["default"].settings_dict
        url = URL.create(
            "postgresql+psycopg2",
            username=config["USER"] or None,
            password=config["PASSWORD"] or None,
            host=config["HOST"] or None,
            port=config["PORT"] or None,
            database=config["NAME"],
        )
        # Neon requires TLS, and Django carries that in OPTIONS rather than the host.
        sslmode = (config.get("OPTIONS") or {}).get("sslmode")

        return create_engine(url, connect_args={"sslmode": sslmode} if sslmode else {})

    def _get_latest_files(self, run_id: str = None) -> dict:
        if settings.STORAGE == "gcs":
            return ObjectStorageService().get_storage().read_run(run_id=run_id)
        return self._get_latest_files_using_path(run_id=run_id)

    def _get_latest_files_using_path(self, run_id: str = None) -> dict:
        # Paths are nba_data/<run_id>/season=<season_id>/<table>.parquet
        parent_path = Path(self.file_path_parent_name)
        if not parent_path.exists():
            logger.warning(f"Parent path {self.file_path_parent_name} does not exist. No data loaded into DuckDB.")
            return {}
        if run_id is not None:
            # name the run explicitly so a concurrent backfill isn't loaded instead
            latest_run_id = run_id
            if not (parent_path / latest_run_id).is_dir():
                raise FileNotFoundError(f"Run {latest_run_id} not found under {self.file_path_parent_name}")
            logger.info(f"Loading explicitly requested run_id: {latest_run_id}")
        else:
            run_ids = [d.name for d in parent_path.iterdir() if d.is_dir()]
            if not run_ids:
                logger.warning(f"No run_id directories found in {self.file_path_parent_name}. No data loaded into DuckDB.")
                return {}
            latest_run_id = max(run_ids)
            logger.info(f"Latest run_id found: {latest_run_id}")
        latest_run_path = parent_path / latest_run_id
        table_dict = {}
        for season_dir in latest_run_path.iterdir():
            if season_dir.is_dir() and season_dir.name.startswith("season="):
                for file in season_dir.iterdir():
                    if file.is_file() and file.suffix == f".{settings.FILE_FORMAT}":
                        table_name = file.stem
                        try:
                            prev_df = table_dict.get(table_name, pd.DataFrame())
                            df = pd.read_parquet(file)
                            if prev_df.empty:
                                table_dict[table_name] = df
                            else:
                                all_df = pd.concat([prev_df, df], ignore_index=True)
                                table_dict[table_name] = all_df
                            logger.info(f"Loaded file {file} into DataFrame for table {table_name}")
                        except Exception:
                            logger.exception(f"Failed to read parquet file: {file}")
        return table_dict
    
    def save(self, run_id: str = None) -> dict:
        logger.info("Starting upsert of NBA data into the database")
        dfs = self._get_latest_files(run_id=run_id)
        loaded = {}
        try:
            for table_name, model in self.table_model_map.items():
                df: dict = dfs.get(table_name)
                logger.info(f"Upserting data for table: {table_name}, Number of records: {len(df) if df is not None else 0}")
                # None just means this table wasn't part of the run
                if df is not None and not df.empty:
                    logger.info(f"Upserting data for table: {table_name}")
                    # NaN -> None, or sparse fields store the literal string "nan"
                    df = df.where(pd.notnull(df), None)
                    records = df.to_dict(orient="records")
                    table_model = TableModelFactory.get_table_model(table_name)
                    table_model.upsert_many(model, records)
                    loaded[table_name] = len(records)
        except Exception as e:
            logger.error(f"Error during upsert operation: {e}")
            raise

        logger.info(f"Upsert complete: {loaded}")
        return loaded
    
    def read(self, table_name: str, df: bool = True):
        model = self.table_model_map[table_name]
        table_model = TableModelFactory.get_table_model(table_name)
        model_list = table_model.read(model)

        if df:
            return pd.DataFrame(model_list)

        return model_list