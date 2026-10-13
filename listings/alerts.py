"""Alerts: tell a human when a task has failed for good (after its retries).

Here the alert is a line in data/alerts.log. In a real deployment this function
would post to Slack or send an email instead; the DAG does not change.
"""

from datetime import datetime, timezone

from listings.config import DATA_DIR

ALERTS_FILE = DATA_DIR / "alerts.log"


def notify_failure(context) -> None:
    ti = context["ti"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"{now} FAILED {ti.dag_id}.{ti.task_id} run={context['run_id']} error={context.get('exception')!r}"
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
