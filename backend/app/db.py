from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import config

pool = ConnectionPool(
    config.DATABASE_URL,
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row},
    open=False,
)


def init_pool() -> None:
    pool.open()
    pool.wait()


def query_one(sql: str, params=None):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def query_all(sql: str, params=None):
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def execute(sql: str, params=None) -> int:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.rowcount


def execute_script(sql_text: str) -> None:
    # psycopg3 (protocolo estendido) executa um comando por vez; dividimos o
    # script em statements. O schema nao contem ';' dentro de literais.
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    with pool.connection() as conn, conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)
