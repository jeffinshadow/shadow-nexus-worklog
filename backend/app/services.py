"""Leituras agregadas (board, dashboard, relatorios).

Todas as funcoes recebem um user_id EXPLICITO. Quem decide qual user_id passar
sao as rotas (proprio usuario, ou alvo validado por require_admin). Assim a
mesma logica serve tanto o usuario comum quanto a visao de admin.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import db
from .config import config


def app_today() -> date:
    return datetime.now(ZoneInfo(config.APP_TZ)).date()


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


# Datas de referência (hoje / início da semana=DOMINGO / início do mês) no fuso
# da aplicação. EXTRACT(DOW) usa domingo=0, então week_start = today - DOW
# (evita o date_trunc('week') do Postgres, que começaria na segunda).
_REF_DATES = """
    WITH p AS (
        SELECT
            d.today,
            d.today - CAST(EXTRACT(DOW FROM d.today) AS int) AS week_start,
            date_trunc('month', d.today)::date               AS month_start
        FROM (SELECT (now() AT TIME ZONE %(tz)s)::date AS today) d
    )
"""

# Grupo A — recorrentes. Um "slot" = (uma recorrente vigente em um dia D do
# período). Vigência de cada tarefa = [start_d, end_d]:
#   start_d = created_at::date  (no fuso da app)
#   end_d   = COALESCE(deactivated_at::date, hoje)   (inclusive)
# Assim: tarefa ativa conta até hoje; tarefa desativada conta só até o dia da
# desativação (dias posteriores NÃO geram slots); tarefa criada no meio do
# período não infla dias anteriores à criação.
#
# Denominador (slots) = soma, por tarefa, dos dias do período ∩ [start_d, end_d].
# Numerador (done) = completions cujo dia caiu DENTRO da vigência da tarefa —
# NÃO filtramos por `active` de hoje, senão o histórico de tarefas desativadas
# sumiria. (Toda completion foi criada num dia em que a tarefa estava vigente.)
#
# Reativação: o endpoint zera deactivated_at e AVANÇA created_at para agora, ou
# seja a vigência recomeça — os dias mortos não voltam ao denominador nem as
# completions antigas ao numerador (ver recurring.py).
#
# LEAST(week_start, month_start): no início do mês a semana atual pode começar
# no mês anterior; a janela de busca precisa cobrir semana E mês.
_DASH_RECURRING_SQL = _REF_DATES + """
    , tw AS (
        SELECT
            r.id,
            (r.created_at AT TIME ZONE %(tz)s)::date AS start_d,
            COALESCE((r.deactivated_at AT TIME ZONE %(tz)s)::date, p.today) AS end_d
          FROM p, recurring_tasks r
         WHERE r.user_id = %(uid)s
    ),
    slots AS (
        SELECT
            COALESCE(SUM(GREATEST(LEAST(p.today, tw.end_d) - GREATEST(p.today,       tw.start_d) + 1, 0)), 0)::int AS day_slots,
            COALESCE(SUM(GREATEST(LEAST(p.today, tw.end_d) - GREATEST(p.week_start,  tw.start_d) + 1, 0)), 0)::int AS week_slots,
            COALESCE(SUM(GREATEST(LEAST(p.today, tw.end_d) - GREATEST(p.month_start, tw.start_d) + 1, 0)), 0)::int AS month_slots
          FROM p, tw
    ),
    done AS (
        SELECT
            count(*) FILTER (WHERE c.completed_date =  p.today)::int       AS day_done,
            count(*) FILTER (WHERE c.completed_date >= p.week_start)::int  AS week_done,
            count(*) FILTER (WHERE c.completed_date >= p.month_start)::int AS month_done
          FROM p
          LEFT JOIN (recurring_completions c JOIN tw ON tw.id = c.task_id)
                 ON c.user_id = %(uid)s
                AND c.completed_date BETWEEN LEAST(p.week_start, p.month_start) AND p.today
                AND c.completed_date BETWEEN tw.start_d AND tw.end_d
    )
    SELECT
        done.day_done,
        GREATEST(slots.day_slots   - done.day_done,   0) AS day_open,
        done.week_done,
        GREATEST(slots.week_slots  - done.week_done,  0) AS week_open,
        done.month_done,
        GREATEST(slots.month_slots - done.month_done, 0) AS month_open
      FROM p, slots, done
"""

# Grupo B — pontuais. Concluído = worklog 'done' com completed_at no período
# (no fuso da app). "Em aberto" = backlog atual (status <> 'done'), igual para
# os três períodos por definição (escolha documentada).
_DASH_PONTUAL_SQL = _REF_DATES + """
    SELECT
        (SELECT count(*) FROM worklog_tasks
          WHERE user_id = %(uid)s AND status <> 'done')::int AS open_now,
        count(*) FILTER (WHERE (w.completed_at AT TIME ZONE %(tz)s)::date =  p.today)::int       AS day_done,
        count(*) FILTER (WHERE (w.completed_at AT TIME ZONE %(tz)s)::date >= p.week_start)::int  AS week_done,
        count(*) FILTER (WHERE (w.completed_at AT TIME ZONE %(tz)s)::date >= p.month_start)::int AS month_done
      FROM p
      LEFT JOIN worklog_tasks w
             ON w.user_id = %(uid)s
            AND w.status = 'done'
            AND w.completed_at IS NOT NULL
            -- LEAST: cobre também a semana atual quando ela começa no mês anterior.
            AND (w.completed_at AT TIME ZONE %(tz)s)::date
                BETWEEN LEAST(p.week_start, p.month_start) AND p.today
"""


def get_dashboard(user_id: int) -> dict:
    params = {"uid": user_id, "tz": config.APP_TZ}
    a = db.query_one(_DASH_RECURRING_SQL, params)
    b = db.query_one(_DASH_PONTUAL_SQL, params)
    return {
        "recurring": {
            "day":   {"done": a["day_done"],   "open": a["day_open"]},
            "week":  {"done": a["week_done"],  "open": a["week_open"]},
            "month": {"done": a["month_done"], "open": a["month_open"]},
        },
        "pontual": {
            "day":   {"done": b["day_done"],   "open": b["open_now"]},
            "week":  {"done": b["week_done"],  "open": b["open_now"]},
            "month": {"done": b["month_done"], "open": b["open_now"]},
        },
    }


def get_report_range(user_id: int, start: date, end: date) -> dict:
    """Dados do 'Relatorio Worklog' para extracao em PDF, dia a dia.

    So entram DIAS COM ATIVIDADE = houve alguma recorrente concluida OU alguma
    pontual concluida naquele dia. Em cada dia listamos as recorrentes VIGENTES
    naquele dia (concluidas e nao concluidas) e as pontuais concluidas no dia.

    Vigencia de cada recorrente = [start_d, end_d] (no fuso da app):
      start_d = created_at::date;  end_d = COALESCE(deactivated_at::date, hoje).
    'end' e limitado a hoje pela rota (sem dias futuros).
    """
    tz = config.APP_TZ

    tasks = db.query_all(
        """
        SELECT r.id, r.label,
               (r.created_at AT TIME ZONE %s)::date AS start_d,
               COALESCE((r.deactivated_at AT TIME ZONE %s)::date,
                        (now() AT TIME ZONE %s)::date) AS end_d
          FROM recurring_tasks r
         WHERE r.user_id = %s
         ORDER BY r.position, r.id
        """,
        (tz, tz, tz, user_id),
    )
    completions = db.query_all(
        """
        SELECT task_id, completed_date
          FROM recurring_completions
         WHERE user_id = %s AND completed_date BETWEEN %s AND %s
        """,
        (user_id, start, end),
    )
    worklog = db.query_all(
        """
        SELECT title, description,
               (completed_at AT TIME ZONE %s)::date AS done_date
          FROM worklog_tasks
         WHERE user_id = %s AND status = 'done' AND completed_at IS NOT NULL
           AND (completed_at AT TIME ZONE %s)::date BETWEEN %s AND %s
         ORDER BY completed_at
        """,
        (tz, user_id, tz, start, end),
    )

    done_by_date: dict[date, set[int]] = {}
    for c in completions:
        done_by_date.setdefault(c["completed_date"], set()).add(c["task_id"])
    pont_by_date: dict[date, list] = {}
    for w in worklog:
        pont_by_date.setdefault(w["done_date"], []).append(
            {"title": w["title"], "description": w["description"]}
        )

    active_dates = sorted(set(done_by_date) | set(pont_by_date))

    days = []
    total_done = total_slots = total_pont = 0
    for d in active_dates:
        done_ids = done_by_date.get(d, set())
        rec = [
            {"label": t["label"], "done": t["id"] in done_ids}
            for t in tasks
            if t["start_d"] <= d <= t["end_d"]
        ]
        n_done = sum(1 for r in rec if r["done"])
        pont = pont_by_date.get(d, [])
        days.append(
            {
                "date": d,
                "recurring": rec,
                "recurring_done": n_done,
                "recurring_total": len(rec),
                "pontual": pont,
            }
        )
        total_done += n_done
        total_slots += len(rec)
        total_pont += len(pont)

    return {
        "start": start,
        "end": end,
        "days": days,
        "summary": {
            "recurring_done": total_done,
            "recurring_total": total_slots,
            "pontual_done": total_pont,
            "active_days": len(days),
        },
    }
