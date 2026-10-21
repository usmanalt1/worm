import django_setup  # noqa: F401  # configure Django before assets import backend code

from dagster import (
    AssetSelection,
    DefaultScheduleStatus,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    in_process_executor,
)

from alerts import email_alert_sensors
from assets import (
    backtest_scorecard,
    bigquery_tables,
    dbt_marts,
    latest_nba_data,
    live_predictions,
    postgres_raw_tables,
    team_strength,
)

# in_process: the assets are sequential, so forking only re-imports Django and sklearn
# per child - and the multiprocess executor SIGBUSes in this container.
nightly_pipeline = define_asset_job(
    "nightly_pipeline",
    selection=AssetSelection.assets(
        latest_nba_data, postgres_raw_tables, dbt_marts, team_strength, live_predictions,
    ),
    executor_def=in_process_executor,
    description="Collect the live season, load it, rebuild the marts, re-predict the upcoming slate.",
)

backtest_pipeline = define_asset_job(
    "backtest_pipeline",
    selection=AssetSelection.assets(backtest_scorecard),
    executor_def=in_process_executor,
    description="Score every strategy against the last completed season.",
)

# 09:00 London = 04:00 ET, after the last west-coast game. Explicit timezone, or this
# drifts against the games twice a year.
nightly_schedule = ScheduleDefinition(
    name="nightly_pipeline_schedule",
    job=nightly_pipeline,
    cron_schedule="0 9 * * *",
    execution_timezone="Europe/London",
    default_status=DefaultScheduleStatus.RUNNING,
)

# Stopped by default; mainly useful out of season or after a model change.
backtest_schedule = ScheduleDefinition(
    name="backtest_pipeline_schedule",
    job=backtest_pipeline,
    cron_schedule="0 11 * * 1",
    execution_timezone="Europe/London",
    default_status=DefaultScheduleStatus.STOPPED,
)

defs = Definitions(
    assets=[
        latest_nba_data,
        postgres_raw_tables,
        dbt_marts,
        team_strength,
        live_predictions,
        backtest_scorecard,
        bigquery_tables,
    ],
    jobs=[nightly_pipeline, backtest_pipeline],
    schedules=[nightly_schedule, backtest_schedule],
    sensors=email_alert_sensors(nightly_pipeline),
)
