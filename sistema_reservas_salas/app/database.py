# app/database.py
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error
from flask import current_app, g


def get_db():
    """
    Retorna a conexão MySQL ativa para a requisição atual.
    A conexão é emprestada de um "pool" (estoque de conexões prontas)
    e devolvida a ele automaticamente no final da requisição.
    """
    if "db_conn" not in g or not g.db_conn.is_connected():
        g.db_conn = mysql.connector.connect(
            pool_name="salafacil_pool",
            pool_size=current_app.config["DB_POOL_SIZE"],
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            charset="utf8mb4",
            autocommit=False,
            connection_timeout=10,
        )
    return g.db_conn


def query_all(sql, params=None):
    """Executa um SELECT e retorna uma lista de dicionários."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()


def query_one(sql, params=None):
    """Executa um SELECT e retorna apenas um dicionário (ou None)."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchone()
    finally:
        cursor.close()


def execute_write(sql, params=None, commit=True):
    """
    Executa INSERT, UPDATE ou DELETE.
    Retorna o lastrowid (útil em INSERTs) ou o número de linhas afetadas.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params or ())
        if commit:
            conn.commit()
        return cursor.lastrowid or cursor.rowcount
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()


@contextmanager
def transacao():
    """
    Agrupa VÁRIOS comandos em uma única transação: ou todos valem, ou nenhum vale.
    Uso:
        with transacao() as cursor:
            cursor.execute("INSERT ...", (...))
            cursor.execute("UPDATE ...", (...))
    Se acontecer qualquer erro dentro do bloco 'with', tudo é desfeito (rollback).
    """
    conn = get_db()
    conn.commit()  # fecha leituras anteriores da requisição, para enxergar dados recém-gravados por outros
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def close_db(exception=None):
    """Fecha a conexão MySQL ao final do ciclo de vida da requisição HTTP."""
    db_conn = g.pop("db_conn", None)
    if db_conn is not None and db_conn.is_connected():
        db_conn.close()


def init_db_app(app):
    """Registra o fechamento automático da conexão no Flask."""
    app.teardown_appcontext(close_db)
