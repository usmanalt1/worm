"""Email a pipeline outcome from CI, where no dagster-daemon exists to run the sensors.

Usage: python scripts/pipeline_alert.py <job-status> [--run-url URL]
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from config.logger import get_logger  # noqa: E402
from services.notifications.email_service import send_alert_email  # noqa: E402

logger = get_logger(__name__)

JOB_NAME = "nightly_pipeline"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("status", help="GitHub Actions job.status: success, failure or cancelled")
    parser.add_argument("--run-url", default="")
    args = parser.parse_args()

    succeeded = args.status.lower() == "success"
    if succeeded:
        subject = f"[NBA pipeline] {JOB_NAME} succeeded"
        body = [f"{JOB_NAME} completed every step."]
    else:
        subject = f"[NBA pipeline] {JOB_NAME} FAILED ({args.status})"
        body = [
            f"{JOB_NAME} ended with status: {args.status}.",
            "The failing step is the first red one in that run.",
        ]
    if args.run_url:
        body += ["", f"Logs: {args.run_url}"]

    if not send_alert_email(subject, "\n".join(body)):
        logger.error("GMAIL_APP_PASSWORD unset; no alert sent.")
        return 1

    logger.info("Alert sent: %s", subject)
    return 0


if __name__ == "__main__":
    sys.exit(main())
