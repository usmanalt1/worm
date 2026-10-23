
from services.data_collection.collect import CollectRawNBAData
from services.data_collection.pipeline import CollectionPipeline
from services.data_collection.presets import (
    CORE_TABLES,
    LOG_TABLES,
    NIGHTLY_TABLES,
    SEASON_BACKFILL_TABLES,
)
from services.data_collection.request import (
    ALL_SEASON_TYPES,
    PLAYOFFS,
    PRESEASON,
    REGULAR,
    CollectionRequest,
    season_year_for,
)
from services.data_collection.constants import Constants
from services.object_storage.service import ObjectStorageService
from datetime import datetime, timedelta
from django.utils import timezone
from app.models import PlayerAwards
import logging
import pandas as pd
import time

logger = logging.getLogger(__name__)

class BuildDataService:
    def __init__(self, date = None):
        self.date = date or datetime.today() - timedelta(weeks=52)
        self.pipeline = CollectionPipeline()

    def build_nba_data(self, table_name = None, season_id: str = None, season_year: str = None, team_roster: bool = False, game_schedule: bool = False) -> dict:
        """Collect tables into frames without saving them, keyed by table name."""
        # season_id is derived from season_year; it stays in the signature for callers.
        request = CollectionRequest(
            seasons=(season_year or season_year_for(datetime.today().date()),),
            season_types=ALL_SEASON_TYPES,
            tables=self._tables_for(table_name, team_roster, game_schedule),
        )
        try:
            return self.pipeline.frames(request)
        except Exception as e:
            logger.error(f"Error occurred while building NBA data: {e}")
            raise

    @staticmethod
    def _tables_for(table_name: str, team_roster: bool, game_schedule: bool) -> tuple:
        if table_name:
            return (table_name,)
        if game_schedule:
            return (Constants.GAME_SCHEDULE,)
        if team_roster:
            return CORE_TABLES + (Constants.TEAMS_ROSTER,)
        return CORE_TABLES

    def build_player_awards(self, players_table: pd.DataFrame) -> dict:
        """Fetch awards to object storage, skipping stored players: awards are static
        history and the endpoint is rate-limited."""
        existing_player_ids = set(PlayerAwards.objects.values_list("player_id", flat=True).distinct())
        players_to_fetch = players_table[~players_table["player_id"].isin(existing_player_ids)]

        logger.info(
            f"{len(existing_player_ids)} players already have awards data; "
            f"fetching {len(players_to_fetch)} of {len(players_table)} total players"
        )

        if players_to_fetch.empty:
            return {"fetched": 0, "saved": 0, "skipped": len(players_table)}

        collector = CollectRawNBAData(date_to_run=self.date)
        df_awards = collector._get_player_awards(df_players=players_to_fetch)

        saved = 0
        if not df_awards.empty:
            # the response carries columns the model deliberately doesn't store
            model_fields = {f.name for f in PlayerAwards._meta.get_fields() if f.concrete and f.name != "id"}
            df_awards = df_awards[[c for c in df_awards.columns if c in model_fields]]
            df_awards["run_timestamp"] = timezone.now()

            object_storage_service = ObjectStorageService().get_storage()
            object_storage_service.save(df=df_awards, file_name="player_awards", season=collector.season_year)
            saved = len(df_awards)

        return {"fetched": len(players_to_fetch), "saved": saved, "skipped": len(existing_player_ids)}

    def build_latest_data(self, run_id: str = None, season_year: str = None) -> dict:
        """Collect the current season into object storage under one run_id.

        The nightly path: season comes from today, and the schedule is included so live
        mode has unplayed games to predict.
        """
        today = datetime.today()
        season_year = season_year or season_year_for(today.date())
        run_id = run_id or pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
        logger.info(f"Collecting latest data for {season_year} under run {run_id}")

        # Two passes under one run_id: the game logs carry preseason, the season-total
        # tables do not, so preseason there stays an explicit backfill.
        season_total_tables = tuple(t for t in NIGHTLY_TABLES if t not in LOG_TABLES)
        saved = self.pipeline.run(CollectionRequest(
            seasons=(season_year,), season_types=ALL_SEASON_TYPES,
            tables=LOG_TABLES, run_id=run_id, as_of=today.date(),
        ))
        saved.update(self.pipeline.run(CollectionRequest(
            seasons=(season_year,), season_types=(REGULAR, PLAYOFFS),
            tables=season_total_tables, run_id=run_id, as_of=today.date(),
        )))

        return {"run_id": run_id, "season_year": season_year, "saved": saved}

    def build_preseason_backfill(self, seasons: list, run_id: str = None) -> dict:
        """Collect preseason box scores only; a full backfill would also rewrite the
        per-(entity, season) tables."""
        request = CollectionRequest(
            seasons=tuple(seasons), season_types=(PRESEASON,),
            tables=LOG_TABLES, run_id=run_id,
        )
        plan = self.pipeline.plan(request)
        return {"run_id": plan.run_id, "seasons": seasons, "saved": self.pipeline.execute(plan)}

    def build_season_backfill(self, seasons: list, run_id: str = None, season_types: list = None, tables: list = None) -> dict:
        """Backfill chosen tables for chosen seasons and season types under one run_id."""
        request = CollectionRequest(
            seasons=tuple(seasons),
            season_types=tuple(season_types) if season_types else (REGULAR,),
            tables=tuple(tables) if tables else SEASON_BACKFILL_TABLES,
            run_id=run_id,
        )
        plan = self.pipeline.plan(request)
        return {
            "run_id": plan.run_id,
            "seasons": seasons,
            "notes": list(plan.notes),
            "saved": self.pipeline.execute(plan),
        }

    def build_draft_history(self, draft_years: list, run_id: str = None) -> dict:
        """Collect whole drafts into object storage.

        A backfill rather than part of the nightly run: a draft is immutable once held,
        so re-collecting it every night would buy nothing.
        """
        run_id = run_id or pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
        storage = ObjectStorageService(generate_run_id=run_id).get_storage()
        run_timestamp = pd.Timestamp.now()
        collector = CollectRawNBAData(date_to_run=self.date)
        saved = {}

        for draft_year in draft_years:
            df = collector._get_draft_history(draft_year=draft_year)
            if df.empty:
                logger.warning(f"No draft history returned for {draft_year}")
                continue

            df["run_timestamp"] = run_timestamp
            storage.save(df=df, file_name=collector.DRAFT_HISTORY, season=df["season"].iloc[0])
            saved[str(draft_year)] = len(df)
            logger.info(f"Saved {len(df)} picks for the {draft_year} draft under run {run_id}")
            time.sleep(1)  # to avoid rate limiting

        return {"run_id": run_id, "draft_years": draft_years, "saved": saved}

    def build_advanced_season_stats(self, seasons: list, season_types: list = None, run_id: str = None) -> dict:
        """Collect season-level advanced stats into object storage; re-running refreshes."""
        request = CollectionRequest(
            seasons=tuple(seasons),
            season_types=tuple(season_types) if season_types else (REGULAR, PLAYOFFS),
            tables=(
                Constants.ADVANCED_PLAYER_SEASON_STATS,
                Constants.ADVANCED_TEAM_SEASON_STATS,
            ),
            run_id=run_id,
        )
        plan = self.pipeline.plan(request)
        return {"seasons": seasons, "saved": self.pipeline.execute(plan)}
