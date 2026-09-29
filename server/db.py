import sqlite3
from contextlib import contextmanager

from server.config import DATABASE_PATH, DATABASE_URL


class DatabaseConnection:
    def __init__(self, connection, is_postgres: bool):
        self.connection = connection
        self.is_postgres = is_postgres

    def execute(self, query: str, parameters=()):
        if self.is_postgres:
            query = query.replace("?", "%s")
        return self.connection.execute(query, parameters)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, exception_type, exception, traceback):
        return self.connection.__exit__(exception_type, exception, traceback)

    def close(self):
        self.connection.close()


def connect_db():
    if DATABASE_URL:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:
            raise RuntimeError("Install psycopg to use DATABASE_URL.") from error
        connection = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        return DatabaseConnection(connection, is_postgres=True)

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return DatabaseConnection(connection, is_postgres=False)


@contextmanager
def database():
    connection = connect_db()
    try:
        with connection:
            yield connection
    finally:
        connection.close()
