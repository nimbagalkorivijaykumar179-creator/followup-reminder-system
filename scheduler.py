"""
Scheduler + Notifier + Escalation Agent.

Runs periodically (e.g. once a day via `schedule` or a cron job) and decides
which commitments need a reminder right now, sends the reminder, and
escalates commitments that have been reminded too many times without
resolution.
"""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db import Commitment, SessionLocal

REMINDER_LEAD_DAYS = 1  # remind 1 day before deadline, in addition to due/overdue
ESCALATION_THRESHOLD = 2  # escalate after this many reminders with no completion


def _should_remind_today(commitment: Commitment, today: date) -> bool:
    if commitment.status != "pending":
        return False

    if not commitment.deadline:
        # No firm deadline — remind weekly-ish based on creation date.
        days_since_created = (today - commitment.created_at.date()).days
        return days_since_created > 0 and days_since_created % 7 == 0

    deadline = date.fromisoformat(commitment.deadline)
    days_until = (deadline - today).days
    # Remind on lead day, on the due date, and every day it's overdue.
    return days_until <= REMINDER_LEAD_DAYS


def notify(commitment: Commitment) -> None:
    """
    Notification stub. Replace with a real Slack webhook / email send.
    Kept as a console print so the pipeline is demoable without external
    services configured.
    """
    status_label = "OVERDUE" if commitment.deadline and date.fromisoformat(
        commitment.deadline
    ) < date.today() else "REMINDER"
    print(
        f"[{status_label}] {commitment.owner}: '{commitment.task}' "
        f"(deadline: {commitment.deadline or 'unspecified'}, "
        f"priority: {commitment.priority}, "
        f"reminder #{commitment.reminder_count + 1})"
    )


def run_daily_check() -> dict:
    """
    Main scheduler entry point. Checks all pending commitments, fires
    reminders where due, and escalates repeatedly-ignored ones.
    Returns a summary dict (useful for tests / API response / logging).
    """
    db: Session = SessionLocal()
    today = date.today()
    reminded, escalated = [], []

    try:
        commitments = db.query(Commitment).filter(Commitment.status.in_(["pending", "escalated"])).all()

        for c in commitments:
            if not _should_remind_today(c, today):
                continue

            notify(c)
            c.reminder_count += 1
            c.last_reminded_at = datetime.utcnow()
            reminded.append(c.id)

            if c.reminder_count >= ESCALATION_THRESHOLD and c.status != "escalated":
                c.status = "escalated"
                c.priority = "high"
                escalated.append(c.id)
                print(f"  -> ESCALATED: commitment {c.id} ignored {c.reminder_count}x, priority raised to high")

        db.commit()
    finally:
        db.close()

    return {"reminded": reminded, "escalated": escalated, "checked_on": today.isoformat()}
