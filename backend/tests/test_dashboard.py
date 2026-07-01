"""Correção dos cálculos do dashboard (Grupo A recorrentes, Grupo B pontuais,
fronteira de semana domingo→sábado). Datas semeadas em relação a 'hoje'; os
esperados são recalculados de forma independente da query."""

from datetime import datetime, timedelta, timezone

from app import db, services
from tests.helpers import TZ, add_recurring, add_worklog, complete, dt

today = services.app_today()
ws = services.week_start(today)
ms = today.replace(day=1)


def dash(uid):
    return services.get_dashboard(uid)


def expected_recurring(created, end, comp_dates):
    """Reimplementação independente da janela de vigência [created, end],
    para conferir o SQL do Grupo A período a período."""
    periods = {"day": (today, today), "week": (ws, today), "month": (ms, today)}
    out = {}
    for key, (ps, pe) in periods.items():
        lo, hi = max(ps, created), min(pe, end)
        slots = (hi - lo).days + 1 if hi >= lo else 0
        done = len([d for d in comp_dates if ps <= d <= pe and created <= d <= end])
        out[key] = {"done": done, "open": max(slots - done, 0)}
    return out


# ----------------- Grupo A: janela de vigência (created_at) -----------------

def test_group_a_task_created_today_adds_one_slot(make_user):
    """REGRESSÃO do bug antigo: uma recorrente criada HOJE deve contribuir com
    apenas 1 slot em Dia/Semana/Mês — não (ativas × dias decorridos)."""
    uid = make_user("a@x.com")
    add_recurring(uid, created_at=dt(today))  # criada hoje, sem completions

    r = dash(uid)["recurring"]
    assert r["day"] == {"done": 0, "open": 1}
    assert r["week"] == {"done": 0, "open": 1}
    assert r["month"] == {"done": 0, "open": 1}

    # Prova de que o denominador NÃO é o do bug antigo quando há dias decorridos.
    buggy_month = (today - ms).days + 1
    if buggy_month > 1:
        assert r["month"]["open"] != buggy_month


def test_group_a_created_mid_period_window(make_user):
    """Denominador por tarefa = dias do período em que a tarefa já existia."""
    uid = make_user("a@x.com")
    created = today - timedelta(days=3)
    add_recurring(uid, created_at=dt(created))

    r = dash(uid)["recurring"]
    exp_week = (today - max(ws, created)).days + 1
    exp_month = (today - max(ms, created)).days + 1
    assert r["day"] == {"done": 0, "open": 1}
    assert r["week"] == {"done": 0, "open": exp_week}
    assert r["month"] == {"done": 0, "open": exp_month}


def test_group_a_completions_and_open(make_user):
    uid = make_user("a@x.com")
    # ativa desde bem antes do mês -> vigente todos os dias do período
    t = add_recurring(uid, created_at=dt(ms - timedelta(days=40)))

    dates = {today}
    if ws != today:
        dates.add(ws)
    if ms < ws:
        dates.add(ms)
    for d in dates:
        complete(t, uid, d)

    day_slots = 1
    week_slots = (today - ws).days + 1
    month_slots = (today - ms).days + 1
    day_done = 1
    week_done = len([d for d in dates if d >= ws])
    month_done = len([d for d in dates if d >= ms])

    r = dash(uid)["recurring"]
    assert r["day"] == {"done": day_done, "open": day_slots - day_done}
    assert r["week"] == {"done": week_done, "open": week_slots - week_done}
    assert r["month"] == {"done": month_done, "open": month_slots - month_done}


def test_group_a_deactivation_preserves_history(make_user):
    """Tarefa desativada: dias ANTES da desativação continuam no numerador E no
    denominador; dias DEPOIS não geram slots."""
    uid = make_user("a@x.com")
    created = min(ws, ms) - timedelta(days=5)  # vigente desde antes do período
    deact = ws  # desativada no início da semana (domingo)
    tid = add_recurring(uid, created_at=dt(created), deactivated_at=dt(deact), active=False)
    complete(tid, uid, ws)  # cumprida no dia da desativação (dentro da janela)

    comp = [ws]
    r = dash(uid)["recurring"]
    assert r == expected_recurring(created, deact, comp)
    # histórico preservado: conta mesmo estando inativa hoje
    assert r["week"]["done"] == 1
    # dias após a desativação não geram slots (vs. se estivesse ativa até hoje)
    if today > deact:
        assert r["week"]["open"] < expected_recurring(created, today, comp)["week"]["open"]


def test_group_a_reactivation_resets_window(make_user, login):
    """Reativar via endpoint: grava/limpa deactivated_at, reinicia a vigência
    (created_at=hoje); dias mortos e completions antigas não voltam a contar."""
    uid = make_user("a@x.com")
    tid = add_recurring(uid, created_at=dt(min(ws, ms) - timedelta(days=5)))
    complete(tid, uid, today - timedelta(days=1))  # cumprida ONTEM (antes de reativar)

    c = login("a@x.com")

    assert c.delete(f"/api/recurring/{tid}").status_code == 200
    row = db.query_one("SELECT active, deactivated_at FROM recurring_tasks WHERE id=%s", (tid,))
    assert row["active"] is False and row["deactivated_at"] is not None

    assert c.patch(f"/api/recurring/{tid}", json={"active": True}).status_code == 200
    row = db.query_one(
        "SELECT active, deactivated_at, created_at FROM recurring_tasks WHERE id=%s", (tid,)
    )
    assert row["active"] is True
    assert row["deactivated_at"] is None
    assert row["created_at"].astimezone(TZ).date() == today  # vigência recomeçou hoje

    # a completion de ontem NÃO conta (fora da nova janela); nada cumprido hoje
    r = dash(uid)["recurring"]
    assert r["day"] == {"done": 0, "open": 1}
    assert r["week"] == {"done": 0, "open": 1}

    # cumprindo hoje, passa a contar
    complete(tid, uid, today)
    assert dash(uid)["recurring"]["day"] == {"done": 1, "open": 0}


# ------------------- Fronteira de semana (domingo→sábado) -------------------

def test_week_starts_on_sunday(make_user):
    uid = make_user("a@x.com")
    assert ws.weekday() == 6  # domingo (Python: segunda=0 .. domingo=6)

    t = add_recurring(uid, created_at=dt(ms - timedelta(days=40)))
    sat_prev = ws - timedelta(days=1)  # sábado da semana anterior
    complete(t, uid, ws)        # domingo = início desta semana -> conta
    complete(t, uid, sat_prev)  # sábado anterior -> NÃO conta na semana
    complete(t, uid, today)

    inserted = {ws, sat_prev, today}
    exp_week_done = len([d for d in inserted if d >= ws])

    r = dash(uid)["recurring"]
    assert r["week"]["done"] == exp_week_done
    # o sábado anterior fica de fora da semana atual:
    assert sat_prev < ws


# --------------------------- Grupo B: pontuais ------------------------------

def test_group_b_periods_and_open(make_user):
    uid = make_user("a@x.com")

    # Datas concluídas em posições distintas. 'before' = dia anterior ao início
    # do período mais cedo (semana OU mês) -> garantidamente fora de tudo.
    before = min(ws, ms) - timedelta(days=1)
    seeded = [today, before]
    if ws != today:
        seeded.append(ws)
    if ms < ws:  # dia do mês antes da semana (quando a semana não cruza o mês)
        seeded.append(ms)
    for d in seeded:
        add_worklog(uid, status="done", completed_at=dt(d))

    # backlog em aberto
    add_worklog(uid, status="todo")
    add_worklog(uid, status="in_progress")
    add_worklog(uid, status="blocked")

    done_day = sum(1 for d in seeded if d == today)
    done_week = sum(1 for d in seeded if ws <= d <= today)
    done_month = sum(1 for d in seeded if ms <= d <= today)
    open_now = 3

    p = dash(uid)["pontual"]
    assert p["day"] == {"done": done_day, "open": open_now}
    assert p["week"] == {"done": done_week, "open": open_now}
    assert p["month"] == {"done": done_month, "open": open_now}
    # a data 'before' não entra em nenhum período
    assert done_day >= 1 and before < ws and before < ms


def test_group_b_timezone_boundary(make_user):
    """completed_at é convertido para APP_TZ antes de virar data.
    America/Sao_Paulo = UTC-3."""
    uid = make_user("a@x.com")

    # 02:00 UTC de hoje == 23:00 SP de ONTEM -> não conta como hoje
    utc_early = datetime(today.year, today.month, today.day, 2, 0, tzinfo=timezone.utc)
    add_worklog(uid, title="utc-cedo", status="done", completed_at=utc_early)
    # 22:00 SP de hoje == 01:00 UTC de amanhã -> conta como hoje
    local_late = dt(today, hour=22)
    add_worklog(uid, title="sp-tarde", status="done", completed_at=local_late)

    p = dash(uid)["pontual"]
    # só o de 22:00 SP é "hoje"
    assert p["day"]["done"] == 1

    # o de 23:00 SP de ontem entra na semana/mês se ontem estiver no período
    yesterday = today - timedelta(days=1)
    exp_week = 1 + (1 if yesterday >= ws else 0)
    exp_month = 1 + (1 if yesterday >= ms else 0)
    assert p["week"]["done"] == exp_week
    assert p["month"]["done"] == exp_month
