"""Success and failure emails for a pipeline run.

These are sensors, so they only fire where a dagster-daemon is running. The GitHub
Actions path runs `dagster job execute` with no daemon and alerts from
scripts/pipeline_alert.py instead.
"""

import os

from dagster import (
    DagsterRunStatus,
    DefaultSensorStatus,
    RunFailureSensorContext,
    RunStatusSensorContext,
    run_failure_sensor,
    run_status_sensor,
)

from services.notifications.email_service import send_alert_email


def _run_lines(run) -> list:
    lines = [f"Run id: {run.run_id}"]
    base = os.getenv("DAGSTER_WEBSERVER_URL")
    if base:
        lines.append(f"Logs: {base.rstrip('/')}/runs/{run.run_id}")
    return lines


def _step_failures(context: RunFailureSensorContext) -> list:
    """`(asset, root cause)` per failed step. `.cause`, since the event's own error is
    only Dagster's "Error occurred while executing op" wrapper."""
    failures = []
    for event in context.get_step_failure_events():
        error = event.event_specific_data.error if event.event_specific_data else None
        cause = (error.cause or error) if error else None
        message = cause.message.strip() if cause else "no error recorded"
        failures.append((event.step_key or "unknown step", message))
    return failures


def email_alert_sensors(job) -> list:
    """A success sensor and a failure sensor emailing the outcome of `job`."""

    @run_status_sensor(
        name=f"{job.name}_success_email",
        run_status=DagsterRunStatus.SUCCESS,
        monitored_jobs=[job],
        # Running by default, like the nightly schedule: an alert nobody enabled is silence.
        default_status=DefaultSensorStatus.RUNNING,
    )
    def on_success(context: RunStatusSensorContext):
        run = context.dagster_run
        body = [f"{run.job_name} completed every asset."] + _run_lines(run)
        send_alert_email(f"[NBA pipeline] {run.job_name} succeeded", "\n".join(body))

    @run_failure_sensor(
        name=f"{job.name}_failure_email",
        monitored_jobs=[job],
        default_status=DefaultSensorStatus.RUNNING,
    )
    def on_failure(context: RunFailureSensorContext):
        run = context.dagster_run
        failures = _step_failures(context)
        failed = ", ".join(step for step, _ in failures) or "unknown step"

        body = [f"{run.job_name} failed at {failed}."] + _run_lines(run)
        for step, message in failures:
            body += ["", f"{step}:", message]

        send_alert_email(
            f"[NBA pipeline] {run.job_name} FAILED at {failed}", "\n".join(body)
        )

    return [on_success, on_failure]
