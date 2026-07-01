"""Isolamento por usuário e autorização de admin (coração da segurança
multiusuário). Exercita as rotas reais via TestClient."""

from fastapi.testclient import TestClient

from app import services
from app.main import app
from tests.helpers import add_recurring, add_worklog, complete, dt

today = services.app_today()


def test_unauthenticated_gets_401():
    c = TestClient(app)
    assert c.get("/api/board").status_code == 401
    assert c.get("/api/dashboard").status_code == 401


def test_board_dashboard_reports_isolated(make_user, login):
    a = make_user("a@x.com")
    b = make_user("b@x.com")

    ta = add_recurring(a, label="A-rec")
    complete(ta, a, today)
    add_worklog(a, title="A-open", status="in_progress")
    add_worklog(a, title="A-done", status="done", completed_at=dt(today))

    add_recurring(b, label="B-rec")
    add_worklog(b, title="B-open", status="todo")

    ca = login("a@x.com")
    cb = login("b@x.com")

    board_a = ca.get("/api/board").json()
    assert [r["label"] for r in board_a["recurring"]] == ["A-rec"]
    titles_a = [x["title"] for x in board_a["in_progress"] + board_a["done"]]
    assert "A-open" in titles_a and "A-done" in titles_a
    assert all(not t.startswith("B-") for t in titles_a)

    board_b = cb.get("/api/board").json()
    assert [r["label"] for r in board_b["recurring"]] == ["B-rec"]
    assert all(not x["title"].startswith("A-") for x in board_b["in_progress"] + board_b["done"])

    # dashboards isolados: A marcou recorrente hoje, B não
    assert ca.get("/api/dashboard").json()["recurring"]["day"]["done"] == 1
    assert cb.get("/api/dashboard").json()["recurring"]["day"]["done"] == 0

    # relatório isolado
    rep_a = ca.get("/api/reports/weekly").json()
    assert any(w["title"] == "A-done" for w in rep_a["worklog"])
    rep_b = cb.get("/api/reports/weekly").json()
    assert all(w["title"] != "A-done" for w in rep_b["worklog"])


def test_common_user_forbidden_on_admin_routes(make_user, login):
    make_user("a@x.com")
    b = make_user("b@x.com")
    ca = login("a@x.com")

    assert ca.get("/api/admin/users").status_code == 403
    assert ca.get(f"/api/admin/users/{b}/board").status_code == 403
    assert ca.get(f"/api/admin/users/{b}/dashboard").status_code == 403
    assert ca.get(f"/api/admin/users/{b}/reports/weekly").status_code == 403


def test_admin_reads_target_user_data(make_user, login):
    make_user("admin@x.com", role="admin")
    b = make_user("b@x.com")

    tb = add_recurring(b, label="B-rec")
    complete(tb, b, today)
    add_worklog(b, title="B-done", status="done", completed_at=dt(today))

    cadm = login("admin@x.com")

    users = cadm.get("/api/admin/users").json()
    assert {u["email"] for u in users} == {"admin@x.com", "b@x.com"}

    board = cadm.get(f"/api/admin/users/{b}/board").json()
    assert [r["label"] for r in board["recurring"]] == ["B-rec"]

    # cálculo usa o user_id do ALVO (B marcou hoje -> done 1), não o do admin
    dash = cadm.get(f"/api/admin/users/{b}/dashboard").json()
    assert dash["recurring"]["day"]["done"] == 1
    assert dash["pontual"]["day"]["done"] == 1

    # o próprio dashboard do admin (sem dados) fica zerado
    self_dash = cadm.get("/api/dashboard").json()
    assert self_dash["recurring"]["day"]["done"] == 0
    assert self_dash["pontual"]["day"]["done"] == 0
