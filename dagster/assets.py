"""Nightly pipeline: NBA API -> object storage -> Postgres -> dbt -> live predictions.

Postgres, not BigQuery: the Django models the API serves are managed=False views onto
nba_marts.*. bigquery_tables below is a separate analytics mirror.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

import django_setup  # noqa: F401  # must come before any backend import

from dagster import AssetExecutionContext, Config, MetadataValue, asset

from seasons import current_season, previous_season
from services.data_collection.build_data_service import BuildDataService
from services.db.db_service import DBService
from services.ml_model.models.model_trainer import ModelTraner, MODE_LIVE
from services.ml_model.model_selection import best_strategy
from services.ml_model.prediction_history import persist_predictions
from services.ratings.team_strength_service import TeamStrengthService
from services.redis.redis_client import RedisClient
from services.redis.redis_key_constants import model_run_cache_key, LAST_RUN
from services.warehouse_storage.bigquery.service import BigQueryService

REPO_ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = REPO_ROOT / "pipeline_nba"

# Over one night so a run lives until the next replaces it, under two so a failed
# pipeline serves nothing rather than yesterday's slate.
MODEL_CACHE_TTL_SECONDS = 26 * 60 * 60


class NightlyConfig(Config):
    # None derives from today; pinning it is how a pipeline sticks on last season.
    season_year: str = None
    strategies: list = ["logistic_regression", "random_forest"]
    # Ordered as the season runs; each type is skipped once it has no unplayed games.
    season_types: list = ["preseason", "regular", "playoffs"]
    dbt_target: str = None


def _season(config) -> str:
    return config.season_year or current_season()


@asset(compute_kind="nba_api")
def latest_nba_data(context: AssetExecutionContext, config: NightlyConfig) -> dict:
    """Collect the in-progress season into object storage. Returns the run_id."""
    season_year = _season(config)
    context.log.info(f"Collecting latest data for {season_year}")

    result = BuildDataService().build_latest_data(season_year=season_year)

    context.add_output_metadata({
        "run_id": result["run_id"],
        "season": result["season_year"],
        "tables": MetadataValue.json(result["saved"]),
        "rows_collected": sum(result["saved"].values()),
    })
    return result


@asset(compute_kind="postgres")
def postgres_raw_tables(context: AssetExecutionContext, latest_nba_data: dict) -> dict:
    """Upsert this run's parquet files into the raw Postgres tables dbt reads from."""
    run_id = latest_nba_data["run_id"]
    context.log.info(f"Loading run {run_id} into Postgres")

    loaded = DBService().save(run_id=run_id)

    if not loaded:
        raise RuntimeError(
            f"Run {run_id} loaded no rows into Postgres. Check STORAGE matches where "
            "latest_nba_data wrote: 'local' reads FILE_PATH_PARENT_NAME, 'gcs' reads PARENT_BUCKET."
        )

    context.add_output_metadata({
        "run_id": run_id,
        "tables": MetadataValue.json(loaded),
        "rows_loaded": sum(loaded.values()),
    })
    return loaded


@asset(compute_kind="dbt")
def dbt_marts(context: AssetExecutionContext, config: NightlyConfig, postgres_raw_tables: dict) -> dict:
    """Build the dbt project. `build` not `run`, so a failing test stops downstream models."""
    target = config.dbt_target or os.getenv("DBT_TARGET", "container_postgres")
    command = [
        "dbt", "build",
        "--project-dir", str(DBT_PROJECT_DIR),
        # Explicit, so it has to honour DBT_PROFILES_DIR itself rather than let dbt read it.
        "--profiles-dir", os.getenv("DBT_PROFILES_DIR", str(DBT_PROJECT_DIR)),
        "--target", target,
    ]
    context.log.info(f"Running: {' '.join(command)}")

    process = subprocess.run(command, cwd=str(DBT_PROJECT_DIR), capture_output=True, text=True)
    for line in process.stdout.splitlines():
        context.log.info(line)
    if process.stderr:
        context.log.warning(process.stderr)

    if process.returncode != 0:
        raise RuntimeError(f"dbt build failed against target '{target}' (exit {process.returncode})")

    context.add_output_metadata({
        "target": target,
        "summary": MetadataValue.md(f"```\n{process.stdout[-4000:]}\n```"),
    })
    return {"target": target, "returncode": process.returncode}


@asset(compute_kind="python")
def team_strength(context: AssetExecutionContext, dbt_marts: dict) -> dict:
    """Rate every completed game into mart_team_strength.

    Python, not dbt: each rating update reads the previous game's rating.
    """
    service = TeamStrengthService(DBService().engine)
    rated = service.build()
    rows = service.write(rated)

    leaders = (
        rated.sort_values(["game_date", "game_id"]).groupby("team_id").tail(1)
        .nlargest(10, "elo_post")[["team_id", "elo_post", "form_adj_margin"]]
    )
    context.add_output_metadata({
        "rows": rows,
        "games": int(rated["game_id"].nunique()),
        "leaders": MetadataValue.md(f"```\n{leaders.round(1).to_string(index=False)}\n```"),
    })
    return {"rows": rows}


def _run_one(context: AssetExecutionContext, season: str, season_type: str, strategy: str) -> dict:
    """Train one strategy for one season type, cache it and store its predictions."""
    label = f"{strategy}/{season_type}"
    try:
        result = ModelTraner(
            strategy=strategy, season=season, season_type=season_type, mode=MODE_LIVE,
        ).train()
    except Exception as exc:
        # a season type with no games yet shouldn't fail the whole run
        context.log.warning(f"{label}: skipped - {exc}")
        return {"error": str(exc)}

    RedisClient().set(
        model_run_cache_key(strategy, season, season_type), result, ex=MODEL_CACHE_TTL_SECONDS,
    )
    stored = persist_predictions(
        strategy=strategy, season=season, season_type=season_type,
        predictions=result.predictions,
    )

    for warning in result.warnings or []:
        context.log.warning(f"{label}: {warning}")

    outcome = {"predicted": len(result.predictions), **stored}
    context.log.info(f"{label}: {outcome}")
    return outcome


def _pick_last_run(summary: dict, season: str, season_types: list, strategies: list) -> Optional[dict]:
    """The run the homepage opens on: in the first season type with stored predictions,
    whichever strategy has called those games best, else config order."""
    for season_type in season_types:
        stored = [s for s in strategies if summary.get(f"{s}/{season_type}", {}).get("written")]
        if not stored:
            continue

        return {
            "strategy": best_strategy(season, season_type, stored) or stored[0],
            "season": season,
            "season_type": season_type,
            "mode": MODE_LIVE,
        }
    return None


@asset(compute_kind="python")
def live_predictions(
    context: AssetExecutionContext,
    config: NightlyConfig,
    dbt_marts: dict,
    team_strength: dict,
) -> dict:
    """Predict the upcoming slate for each strategy and season type.

    Depends on team_strength, not just dbt_marts: the trainer reads
    mart_team_strength, so predicting before it is rebuilt would use stale ratings.

    Stored durably as well as cached: Redis is replaced tomorrow night, leaving
    nothing to grade once games are played.
    """
    season = _season(config)
    summary = {}

    for season_type in config.season_types:
        for strategy in config.strategies:
            summary[f"{strategy}/{season_type}"] = _run_one(
                context, season=season, season_type=season_type, strategy=strategy,
            )

    last_run = _pick_last_run(
        summary, season, season_types=config.season_types, strategies=config.strategies,
    )
    if last_run:
        RedisClient().set(LAST_RUN, last_run)
        context.log.info(f"LAST_RUN -> {last_run}")

    context.add_output_metadata({
        "season": season,
        "runs": MetadataValue.json(summary),
        "last_run": MetadataValue.json(last_run or {}),
    })
    return summary


@asset(compute_kind="bigquery")
def bigquery_tables(context: AssetExecutionContext, latest_nba_data: dict) -> dict:
    """Mirror the collected run into BigQuery. Analytics only; the API never reads it."""
    season = latest_nba_data["season_year"]
    context.log.info(f"Loading season {season} into BigQuery")

    BigQueryService().load_latest_data_from_gcs_to_bigquery(seasons=[season])

    context.log.info("Successfully loaded tables into BigQuery")
    return {"seasons": [season]}


class BacktestConfig(Config):
    # defaults to the last completed season
    season_year: str = None
    season_type: str = "regular"
    strategies: list = ["logistic_regression", "random_forest"]


@asset(compute_kind="python")
def backtest_scorecard(context: AssetExecutionContext, config: BacktestConfig, dbt_marts: dict) -> dict:
    """Score each strategy against a finished season, which live mode cannot do."""
    season = config.season_year or previous_season(current_season())
    redis_client = RedisClient()
    metrics = {}

    for strategy in config.strategies:
        context.log.info(f"Backtesting {strategy} on {season} ({config.season_type})")
        trainer = ModelTraner(strategy=strategy, season=season, season_type=config.season_type)
        result = trainer.train()
        redis_client.set(
            model_run_cache_key(strategy, season, config.season_type), result,
            ex=MODEL_CACHE_TTL_SECONDS,
        )
        metrics[strategy] = result.metrics
        for warning in result.warnings or []:
            context.log.warning(f"{strategy}: {warning}")

    context.add_output_metadata({"season": season, "metrics": MetadataValue.json(metrics)})
    return metrics
