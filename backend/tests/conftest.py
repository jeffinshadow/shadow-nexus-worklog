"""Fixtures de teste. Rodam contra um PostgreSQL REAL (não SQLite/mock), pois a
lógica usa EXTRACT(DOW), FILTER e AT TIME ZONE.

Config via env (com defaults para um Postgres local efêmero):
  TEST_DATABASE_URL  (default: postgresql://postgres@127.0.0.1:55432/nexus_test)
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Precisa estar definido ANTES de importar app.config.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://postgres@127.0.0.1:55432/nexus_test"),
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("APP_TZ", "America/Sao_Paulo")
os.environ.setdefault("COOKIE_SECURE", "false")
# Sem seed de admin automático nos testes (criamos usuários explicitamente).
os.environ.pop("ADMIN_EMAIL", None)
os.environ.pop("ADMIN_INITIAL_PASSWORD", None)

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.security import hash_password

_TABLES = "users, sessions, recurring_tasks, recurring_completions, worklog_tasks"


@pytest.fixture(scope="session")
def _app():
    # O context manager dispara o lifespan: abre o pool, roda migrations.
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def clean(_app):
    db.execute(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE")
    yield


@pytest.fixture
def make_user():
    def _make(email, password="senha-de-teste-123", role="user", must_change=False):
        db.execute(
            """INSERT INTO users (email, password_hash, role, must_change_password)
               VALUES (%s, %s, %s, %s)""",
            (email.lower(), hash_password(password), role, must_change),
        )
        return db.query_one("SELECT id FROM users WHERE email = %s", (email.lower(),))["id"]

    return _make


@pytest.fixture
def login():
    def _login(email, password="senha-de-teste-123"):
        client = TestClient(app)
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        return client

    return _login
