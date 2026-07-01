"""Leituras agregadas (board, dashboard, relatorios).

Todas as funcoes recebem um user_id EXPLICITO. Quem decide qual user_id passar
sao as rotas (proprio usuario, ou alvo validado por require_admin). Assim a
mesma logica serve tanto o usuario comum quanto a visao de admin.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import db
from .config import config


def app_today() -> date:
    return datetime.now(ZoneInfo(config.APP_TZ)).date()


def week_start(ref: date) -> date:
    # Semana comeca no DOMINGO. Python: Monday=0..Sunday=6.
    days_since_sunday = (ref.weekday() + 1) % 7
    return ref - timedelta(days=days_since_sunday)


def get_board(user_id: int) -> dict:
    today = app_today()
    recurring = db.query_all(
        """
        SELECT r.id, r.label, r.position,
               (c.id IS NOT NULL) AS done_today
          FROM recurring_tasks r
          LEFT JOIN recurring_completions c
                 ON c.task_id = r.id AND c.completed_date = %s
         WHERE r.user_id = %s AND r.active = true
         ORDER BY r.position, r.id
        """,
        (today, user_id),
    )
    in_progress = db.query_all(
        """
        SELECT id, title, description, status, due_date, created_at
          FROM worklog_tasks
         WHERE user_id = %s AND status <> 'done'
         ORDER BY COALESCE(due_date, DATE '9999-12-31'), created_at
        """,
        (user_id,),
    )
    done = db.query_all(
        """
        SELECT id, title, description, status, due_date, created_at, completed_at
          FROM worklog_tasks
         WHERE user_id = %s AND status = 'done'
         ORDER BY completed_at DESC NULLS LAST
        """,
        (user_id,),
    )
    return {"recurring": recurring, "in_progress": in_progress, "done": done}


def _completions_between(user_id: int, start: date, end: date) -> int:
    row = db.query_one(
        """
        SELECT count(*) AS n
          FROM recurring_completions c
          JOIN recurring_tasks r ON r.id = c.task_id
         WHERE c.user_id = %s AND r.active = true
           AND c.completed_date BETWEEN %s AND %s
        """,
        (user_id, start, end),
    )
    return row["n"]


def get_dashboard(user_id: int) -> dict:
    today = app_today()
    ws = week_start(today)
    ms = today.replace(day=1)

    total_active = db.query_one(
        "SELECT count(*) AS n FROM recurring_tasks WHERE user_id = %s AND active = true",
        (user_id,),
    )["n"]

    week_days = (today - ws).days + 1
    month_days = (today - ms).days + 1

    return {
        "today": {"done": _completions_between(user_id, today, today), "total": total_active},
        "week": {"done": _completions_between(user_id, ws, today), "total": total_active * week_days},
        "month": {"done": _completions_between(user_id, ms, today), "total": total_active * month_days},
    }


def get_weekly_report(user_id: int, ref: date) -> dict:
    ws = week_start(ref)
    we = ws + timedelta(days=6)

    recurring = db.query_all(
        """
        SELECT r.label, c.completed_date
          FROM recurring_completions c
          JOIN recurring_tasks r ON r.id = c.task_id
         WHERE c.user_id = %s AND c.completed_date BETWEEN %s AND %s
         ORDER BY c.completed_date, r.label
        """,
        (user_id, ws, we),
    )
    worklog = db.query_all(
        """
        SELECT title, description, completed_at
          FROM worklog_tasks
         WHERE user_id = %s AND status = 'done'
           AND (completed_at AT TIME ZONE %s)::date BETWEEN %s AND %s
         ORDER BY completed_at
        """,
        (user_id, config.APP_TZ, ws, we),
    )
    return {
        "week_start": ws,
        "week_end": we,
        "recurring": recurring,
        "worklog": worklog,
    }
