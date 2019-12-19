import dataclasses, typing
import sqlite3

class DatabaseEngineCursor(object):
    def execute(self, query: str, args: typing.List[str]):
        pass
    def fetchone(self) -> typing.Any:
        pass
    def fetchall(self) -> typing.List[typing.Any]:
        pass

class DatabaseEngine(object):
    def config(self, hostname: str=None, port: int=None, path: str=None,
            username: str=None, password: str=None):
        self.hostname = hostname
        self.port = port
        self.path = path
        self.username = username
        self.password = password

    def database_name(self):
        return self.path
    def connect(self):
        pass
    def cursor(self) -> DatabaseEngineCursor:
        pass
    def has_table(self, name: str):
        pass

    def execute(self, query: str, args: typing.List[str]):
        pass
    def fetchone(self, query: str, args: typing.List[str]):
        pass
    def fetchall(self, query: str, args: typing.List[str]):
        pass

class SQLite3Cursor(DatabaseEngineCursor):
    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor
    def execute(self, query: str, args: typing.List[str]):
        self._cursor.execute(query, args)
    def fetchone(self):
        return self._cursor.fetchone()
    def fetchall(self):
        return self._cursor.fetchall()
class SQLite3Engine(DatabaseEngine):
    _connection: sqlite3.Connection

    def connect(self):
        sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))
        self._connection = sqlite3.connect(self.path,
            check_same_thread=False, isolation_level=None,
            detect_types=sqlite3.PARSE_DECLTYPES)
        self._connection.execute("PRAGMA foreign_keys = ON")

    def has_table(self, name: str):
        cursor = self.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            [name])
        return cursor.fetchone()[0] == 1

    def cursor(self):
        return SQLite3Cursor(self._connection.cursor())
