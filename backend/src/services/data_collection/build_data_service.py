
from services.data_collection.collect import CollectRawNBAData
from nba_api.stats.library.parameters import SeasonTypePlayoffs, SeasonType, SeasonTypeAllStar
from services.object_storage.service import ObjectStorageService
from datetime import datetime, timedelta
from django.utils import timezone
from app.models import PlayerAwards, AdvancedPlayerSeasonStats, AdvancedTeamSeasonStats
import logging
import pandas as pd
import time

logger = logging.getLogger(__name__)

class BuildDataService:
    def __init__(self, date = None):
        self.date = date or datetime.today() - timedelta(weeks=52)

    def build_nba_data(self, table_name = None, season_id: str = None, season_year: str = None, team_roster: bool = False, game_schedule: bool = False) -> dict:
        try:
            raw_tables = CollectRawNBAData(date_to_run=self.date).gather_and_import_nba_data(table_name=table_name, season_id=season_id, season_year=season_year, team_roster=team_roster, game_schedule=game_schedule)

        except Exception as e:
            logger.error(f"Error occurred while building NBA data: {e}")
            raise

        return raw_tables

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
        if season_year is None:
            season_year = CollectRawNBAData(date_to_run=today).season_year
        split_year = season_year.split("-")
        season_id = f"{split_year[0][-2:]}0{split_year[1][-2:]}"

        run_id = run_id or pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
        storage = ObjectStorageService(generate_run_id=run_id).get_storage()
        run_timestamp = pd.Timestamp.now()
        logger.info(f"Collecting latest data for {season_year} (season_id={season_id}) under run {run_id}")

        collector = BuildDataService(date=today)
        saved = {}

        def _save(tables: dict) -> None:
            for table_name, df in tables.items():
                if df is None or df.empty:
                    logger.warning(f"No rows collected for {table_name} ({season_year})")
                    continue
                df["run_timestamp"] = run_timestamp
                storage.save(df=df, file_name=table_name, season=season_year)
                saved[table_name] = len(df)
                logger.info(f"Saved {len(df)} rows for {table_name} ({season_year}) under run {run_id}")

        _save(collector.build_nba_data(season_id=season_id, season_year=season_year, team_roster=True))
        _save(collector.build_nba_data(season_id=season_id, season_year=season_year, game_schedule=True))
        collector.build_advanced_season_stats(
            seasons=[season_year], storage=storage, run_timestamp=run_timestamp,
        )

        return {"run_id": run_id, "season_year": season_year, "saved": saved}

    def build_preseason_backfill(self, seasons: list, run_id: str = None) -> dict:
        """Collect preseason box scores only; a full backfill would also rewrite the
        per-(entity, season) tables."""
        run_id = run_id or pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
        storage = ObjectStorageService(generate_run_id=run_id).get_storage()
        run_timestamp = pd.Timestamp.now()
        collector = CollectRawNBAData(date_to_run=datetime.today())
        saved = {}

        for season_year in seasons:
            for table_name, pt in ((collector.TEAM_STATS, "T"), (collector.PLAYER_STATS, "P")):
                df = collector._get_logs(
                    season_year=season_year,
                    pt_abbreviation=pt,
                    season_type=SeasonTypeAllStar.preseason,
                )
                df = df.dropna()
                if df.empty:
                    logger.warning(f"No preseason {table_name} for {season_year}")
                    continue
                df["run_timestamp"] = run_timestamp
                storage.save(df=df, file_name=table_name, season=season_year)
                saved[f"{season_year}/{table_name}"] = len(df)
                logger.info(f"Saved {len(df)} preseason {table_name} rows for {season_year}")

        return {"run_id": run_id, "seasons": seasons, "saved": saved}

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

    def build_advanced_season_stats(self, seasons: list, season_types: list = None, storage=None, run_timestamp=None) -> dict:
        """Collect season-level advanced stats into object storage; re-running refreshes."""
        if season_types is None:
            season_types = [SeasonType.default, SeasonTypePlayoffs.playoffs]

        collector = CollectRawNBAData(date_to_run=self.date)
        # Passed in, these fold this into a larger run so every table shares one run_id.
        object_storage_service = storage or ObjectStorageService().get_storage()
        run_timestamp = run_timestamp or timezone.now()
        model_for = {
            collector.ADVANCED_PLAYER_SEASON_STATS: AdvancedPlayerSeasonStats,
            collector.ADVANCED_TEAM_SEASON_STATS: AdvancedTeamSeasonStats,
        }
        saved = {}

        for season_year in seasons:
            split_year = season_year.split("-")
            season_id = f"{split_year[0][-2:]}0{split_year[1][-2:]}"

            # Storage keys on (run, season, table_name), so saving each season_type
            # separately would have the second overwrite the first.
            combined = {table: [] for table in model_for}
            for season_type in season_types:
                raw_tables = collector._get_advanced_season_stats(
                    season_year=season_year, season_id=season_id, season_type=season_type,
                )
                for table_name, df in raw_tables.items():
                    if df is not None and not df.empty:
                        combined[table_name].append(df)

            for table_name, frames in combined.items():
                if not frames:
                    continue
                df = pd.concat(frames, ignore_index=True)
                model = model_for[table_name]
                model_fields = {f.name for f in model._meta.get_fields() if f.concrete and f.name != "id"}
                df = df[[c for c in df.columns if c in model_fields]]
                df["run_timestamp"] = run_timestamp
                object_storage_service.save(df=df, file_name=table_name, season=season_year)
                key = f"{season_year}/{table_name}"
                saved[key] = len(df)
                logger.info(f"Saved {len(df)} rows for {key} to object storage")

        return {"seasons": seasons, "saved": saved}
