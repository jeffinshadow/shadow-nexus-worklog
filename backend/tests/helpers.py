"""Helpers de seeding — inserem dados diretamente via db (com datas/horários
controlados) para asserts determinísticos."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app import db
from app.config import config

TZ = ZoneInfo(config.APP_TZ)


def dt(d, hour=12):
    """Datetime tz-aware no fuso da app (meio-dia por padrão)."""
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=TZ)


def add_recurring(user_id, label="rec", created_at=None, active=True, deactivated_at=None):
    row = db.query_one(
        """INSERT INTO recurring_tasks (user_id, label, active, created_at, deactivated_at)
           VALUES (%s, %s, %s, COALESCE(%s, now()), %s)
           RETURNING id""",
        (user_id, label, active, created_at, deactivated_at),
    )
    return row["id"]


def complete(task_id, user_id, completed_date):
    db.execute(
        """INSERT INTO recurring_completions (task_id, user_id, completed_date)
           VALUES (%s,%s,%s) ON CONFLICT (task_id, completed_date) DO NOTHING""",
        (task_id, user_id, completed_date),
    )


def add_worklog(user_id, title="task", status="todo", completed_at=None,
                due_date=None, description=None):
    row = db.query_one(
        """INSERT INTO worklog_tasks (user_id, title, description, status, due_date, completed_at)
           VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
        (user_id, title, description, status, due_date, completed_at),
    )
    return row["id"]
