import logging
from dataclasses import dataclass, replace

import pandas as pd

from services.data_collection.collectors.registry import build_registry, dataset_for_table
from services.data_collection.request import (
    CollectionRequest,
    WorkItem,
    season_year_for,
)
from services.object_storage.service import ObjectStorageService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectionPlan:
    run_id: str
    items: tuple
    notes: tuple

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "work_items": len(self.items),
            "datasets": sorted({item.dataset for item in self.items}),
            "seasons": sorted({item.season_year for item in self.items}),
            "notes": list(self.notes),
        }


def restrict_to_model_fields(df: pd.DataFrame, model) -> pd.DataFrame:
    """Drop response columns the model does not store, which would break the upsert."""
    model_fields = {f.name for f in model._meta.get_fields() if f.concrete and f.name != "id"}
    return df[[c for c in df.columns if c in model_fields]]


class CollectionPipeline:
    def __init__(self, registry: dict = None):
        self.registry = registry or build_registry()

    def run(self, request: CollectionRequest, storage=None) -> dict:
        return self.execute(self.plan(request), storage=storage)

    def plan(self, request: CollectionRequest) -> CollectionPlan:
        """Resolve the request into work items without calling the API."""
        run_id = request.run_id or pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
        datasets = self._datasets_for(request)
        items, notes = [], []

        for dataset in datasets:
            collector = self.registry[dataset]
            if not collector.backfillable:
                snapshot_season = season_year_for(request.as_of)
                items.append(WorkItem(dataset, snapshot_season, None, request.as_of))
                notes.append(
                    f"{dataset}: live snapshot with no history, collected once for {request.as_of}"
                )
                continue

            for season_year in request.seasons:
                if collector.by_season_type:
                    items.extend(
                        WorkItem(dataset, season_year, season_type, request.as_of)
                        for season_type in request.season_types
                    )
                else:
                    items.append(WorkItem(dataset, season_year, None, request.as_of))

        ignored = [d for d in datasets if not self.registry[d].by_season_type and self.registry[d].backfillable]
        if len(request.season_types) > 1 and ignored:
            notes.append(f"season_types does not apply to: {', '.join(ignored)}")

        return CollectionPlan(run_id=run_id, items=tuple(items), notes=tuple(notes))

    def collect(self, plan: CollectionPlan) -> dict:
        """Run the plan, returning one frame per (season, dataset) with season types merged."""
        parts, cache = {}, {}
        for item in plan.items:
            df = self._fetch(item, cache)
            if df is None or df.empty:
                logger.warning(f"No rows collected for {item.dataset} ({item.season_year})")
                continue
            parts.setdefault((item.season_year, item.dataset), []).append(df)

        collected = {}
        for (season_year, dataset), frames in parts.items():
            collector = self.registry[dataset]
            df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
            if collector.dedupe_on:
                df = df.drop_duplicates(subset=list(collector.dedupe_on), keep="last")
            if collector.model:
                df = restrict_to_model_fields(df, collector.model)
            collected[(season_year, dataset)] = df

        return collected

    def execute(self, plan: CollectionPlan, storage=None) -> dict:
        """Collect and save every table in the plan under its one run_id."""
        logger.info(f"Collection plan: {plan.summary()}")
        storage = storage or ObjectStorageService(generate_run_id=plan.run_id).get_storage()
        run_timestamp = pd.Timestamp.now()
        saved = {}

        for (season_year, dataset), df in self.collect(plan).items():
            table = self.registry[dataset].table
            df["run_timestamp"] = run_timestamp
            storage.save(df=df, file_name=table, season=season_year)
            saved[table] = saved.get(table, 0) + len(df)
            logger.info(
                f"Saved {len(df)} rows for {table} ({season_year}) under run {plan.run_id}"
            )

        return saved

    def frames(self, request: CollectionRequest) -> dict:
        """Collected frames keyed by table, nothing written. Seasons are concatenated."""
        collected = self.collect(self.plan(request))
        by_table = {}
        for (_, dataset), df in collected.items():
            table = self.registry[dataset].table
            by_table.setdefault(table, []).append(df)
        return {
            table: pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
            for table, frames in by_table.items()
        }

    def _datasets_for(self, request: CollectionRequest) -> list:
        if not request.tables:
            return list(self.registry)
        wanted = {dataset_for_table(table) for table in request.tables}
        # Registry order, so dependencies are collected before the datasets needing them.
        return [dataset for dataset in self.registry if dataset in wanted]

    def _fetch(self, item: WorkItem, cache: dict) -> pd.DataFrame:
        key = (item.dataset, item.season_year)
        if item.season_type is None and key in cache:
            return cache[key]

        collector = self.registry[item.dataset]
        deps = {name: self._fetch_dependency(name, item, cache) for name in collector.requires}
        df = collector.fetch(item, deps)

        if item.season_type is None:
            cache[key] = df
        return df

    def _fetch_dependency(self, name: str, item: WorkItem, cache: dict) -> pd.DataFrame:
        # No dependency has a season-type dimension, so one frame per season serves them all.
        return self._fetch(replace(item, dataset=name, season_type=None), cache)
