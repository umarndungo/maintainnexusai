"""
APScheduler Configuration — Periodic Pipeline Execution.

Runs the ETL pipeline on a fixed interval (every 5 minutes by default)
using a sample alert. This simulates a production scenario where
equipment alerts are processed automatically without human intervention.

Start with::

    python database/scheduler.py
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from etl.pipeline import process_alert_pipeline

# BlockingScheduler runs in the foreground of its own process.
# For a web-deployed app, consider ``BackgroundScheduler`` instead.
scheduler = BlockingScheduler()


@scheduler.scheduled_job("interval", minutes=5)
def scheduled_pipeline_run():
    """
    Cron-like job: execute the full ETL pipeline against a sample alert.

    The sample alert mimics a pump-seal failure event. In production the
    alert would arrive via the POST /alerts/maintenance endpoint and be
    persisted to a queue before the scheduler picks it up.

    This job runs every 5 minutes (the ``minutes=5`` argument to the
    decorator). Adjust the interval to match your SLA requirements.
    """
    sample_alert = {
        "equipment_id": "PUMP-901",
        "part_number": "Pump Seal Kit #A4",
        "severity": "HIGH",
        "failure_code": "ERR_SEAL_LEAK",
    }
    # Run the pipeline — ``print`` calls inside the pipeline will surface
    # here so the scheduler logs show what happened.
    process_alert_pipeline(sample_alert)


if __name__ == "__main__":
    # ``scheduler.start()`` blocks forever. Kill the process (Ctrl+C) to stop.
    scheduler.start()
