
import json, os, sqlite3, threading, time

class Database(object):
    def __init__(self, bot, location="bot.db"):
        self.bot = bot
        self.location = location
        self.full_location = os.path.join(bot.bot_directory,
            self.location)
        self.database = sqlite3.connect(self.full_location,
            check_same_thread=False, isolation_level=None)
        self.database.execute("PRAGMA foreign_keys = ON")
        self._cursor = None

        self.make_servers_table()
        self.make_bot_settings_table()
        self.make_server_settings_table()
        self.make_channel_settings_table()
        self.make_user_settings_table()
        self.make_user_channel_settings_table()

    def cursor(self):
        if self._cursor == None:
            self._cursor = self.database.cursor()
        return self._cursor

    def _execute_fetch(self, query, fetch_func, params=[]):
        printable_query = " ".join(query.split())
        self.bot.events.on("log.debug").call(
            message="executing query: \"%s\" (params: %s)",
            params=[printable_query, params])
        start = time.time()

        cursor = self.cursor()
        cursor.execute(query, params)
        value = fetch_func(cursor)

        end = time.time()
        total_milliseconds = (end - start) * 1000
        self.bot.events.on("log.debug").call(
            message="executed in %fms",
            params=[total_milliseconds])
        return value
    def execute_fetchall(self, query, params=[]):
        return self._execute_fetch(query,
            lambda cursor: cursor.fetchall(), params)
    def execute_fetchone(self, query, params=[]):
        return self._execute_fetch(query,
            lambda cursor: cursor.fetchone(), params)
    def execute(self, query, params=[]):
        return self._execute_fetch(query, lambda cursor: None, params)

    def make_servers_table(self):
        try:
            self.execute("""CREATE TABLE servers
                (server_id INTEGER PRIMARY KEY,
                hostname TEXT, port INTEGER, password TEXT,
                ipv4 BOOLEAN, tls BOOLEAN, nickname TEXT,
                username TEXT, realname TEXT)""")
        except sqlite3.Error as e:
            pass
    def make_bot_settings_table(self):
        try:
            self.execute("""CREATE TABLE bot_settings
                (setting TEXT PRIMARY KEY, value TEXT)""")
        except sqlite3.Error as e:
            pass
    def make_server_settings_table(self):
        try:
            self.execute("""CREATE TABLE server_settings
                (server_id INTEGER, setting TEXT, value TEXT,
                FOREIGN KEY(server_id) REFERENCES
                servers(server_id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, setting))""")
        except sqlite3.Error as e:
            pass
    def make_channel_settings_table(self):
        try:
            self.execute("""CREATE TABLE channel_settings
                (server_id INTEGER, channel TEXT, setting TEXT,
                value TEXT, FOREIGN KEY (server_id) REFERENCES
                servers(server_id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, channel, setting))""")
        except sqlite3.Error as e:
            pass
    def make_user_settings_table(self):
        try:
            self.execute("""CREATE TABLE user_settings
                (server_id INTEGER, nickname TEXT, setting TEXT,
                value TEXT, FOREIGN KEY (server_id) REFERENCES
                servers(server_id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, nickname, setting))""")
        except sqlite3.Error as e:
            pass
    def make_user_channel_settings_table(self):
        try:
            self.execute("""CREATE TABLE user_channel_settings
                (server_id INTEGER, channel TEXT, nickname TEXT,
                setting TEXT, value TEXT, FOREIGN KEY (server_id)
                REFERENCES servers(server_id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, nickname, channel, setting))""")
        except sqlite3.Error as e:
            pass

    def add_server(self, hostname, port, password, ipv4, tls, nickname,
            username=None, realname=None):
        username = username or nickname
        realname = realname or nickname
        self.execute(
            """INSERT INTO servers (hostname, port, password, ipv4,
            tls, nickname, username, realname) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?)""",
            [hostname, port, password, ipv4, tls, nickname, username, realname])
    def get_servers(self):
        return self.execute_fetchall(
            """SELECT server_id, hostname, port, password, ipv4,
            tls, nickname, username, realname FROM servers""")
    def get_server(self, id):
        return self.execute_fetchone(
            """SELECT server_id, hostname, port, password, ipv4,
            tls, nickname, username, realname FROM servers WHERE
            server_id=?""",
            [id])

    def set_bot_setting(self, setting, value):
        self.execute(
            "INSERT OR REPLACE INTO bot_settings VALUES (?, ?)",
            [setting.lower(), json.dumps(value)])
    def get_bot_setting(self, setting, default=None):
        value = self.execute_fetchone(
            "SELECT value FROM bot_settings WHERE setting=?",
            [setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find_bot_settings(self, pattern, default=[]):
        values = self.execute_fetchall(
            "SELECT setting, value FROM bot_settings WHERE setting LIKE ?",
            [pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_bot_settings_prefix(self, prefix, default=[]):
        return self.find_bot_settings("%s%" % prefix, default)
    def del_bot_setting(self, setting):
        self.execute(
            "DELETE FROM bot_settings WHERE setting=?",
            [setting.lower()])

    def set_server_setting(self, server_id, setting, value):
        self.execute(
            "INSERT OR REPLACE INTO server_settings VALUES (?, ?, ?)",
            [server_id, setting.lower(), json.dumps(value)])
    def get_server_setting(self, server_id, setting, default=None):
        value = self.execute_fetchone(
            """SELECT value FROM server_settings WHERE
            server_id=? AND setting=?""",
            [server_id,setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find_server_settings(self, server_id, pattern, default=[]):
        values = self.execute_fetchall(
            """SELECT setting, value FROM server_settings WHERE
            server_id=? AND setting LIKE ?""",
            [server_id, pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_server_settings_prefix(self, server_id, prefix, default=[]):
        return self.find_server_settings(server_id, "%s%" % prefix, default)
    def del_server_setting(self, server_id, setting):
        self.execute(
            "DELETE FROM server_settings WHERE server_id=? AND setting=?",
            [server_id, setting.lower()])

    def set_channel_setting(self, server_id, channel, setting, value):
        self.execute(
            "INSERT OR REPLACE INTO channel_settings VALUES (?, ?, ?, ?)",
            [server_id, channel.lower(), setting.lower(), json.dumps(value)])
    def get_channel_setting(self, server_id, channel, setting, default=None):
        value = self.execute_fetchone(
            """SELECT value FROM channel_settings WHERE
            server_id=? AND channel=? AND setting=?""",
            [server_id, channel.lower(), setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find_channel_settings(self, server_id, channel, pattern, default=[]):
        values = self.execute_fetchall(
            """SELECT setting, value FROM channel_settings WHERE
            server_id=? AND channel=? setting LIKE '?'""",
            [server_id, channel.lower(), pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_channel_settings_prefix(self, server_id, channel, prefix,
            default=[]):
        return self.find_channel_settings(server_id, channel, "%s%" % prefix,
            default)
    def del_channel_setting(self, server_id, channel, setting):
        self.execute(
            """DELETE FROM channel_settings WHERE
            server_id=? AND channel=? AND setting=?""",
            [server_id, channel.lower(), setting.lower()])

    def set_user_setting(self, server_id, nickname, setting, value):
        self.execute(
            "INSERT OR REPLACE INTO user_settings VALUES (?, ?, ?, ?)",
            [server_id, nickname.lower(), setting.lower(), json.dumps(value)])
    def get_user_setting(self, server_id, nickname, setting, default=None):
        value = self.execute_fetchone(
            """SELECT value FROM user_settings WHERE
            server_id=? AND nickname=? and setting=?""",
            [server_id, nickname.lower(), setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def get_all_user_settings(self, server_id, setting, default=[]):
        values = self.execute_fetchall(
            """SELECT nickname, setting, value FROM user_settings WHERE
            server_id=? AND setting=?""",
            [server_id, setting])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], value[1], json.loads(value[2])
            return values
        return default
    def find_user_settings(self, server_id, nickname, pattern, default=[]):
        values = self.cursor().execute(
            """SELECT setting, value FROM user_settings WHERE
            server_id=? AND nickname=? AND setting LIKE '?'""",
            [server_id, nickname.lower(), pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_user_settings_prefix(self, server_id, nickname, prefix,
            default=[]):
        return self.find_user_settings(server_id, nickname, "%s%" % prefix,
            default)
    def del_user_setting(self, server_id, nickname, setting):
        self.execute(
            """DELETE FROM user_settings WHERE
            server_id=? AND nickname=? AND setting=?""",
            [server_id, nickname.lower(), setting.lower()])

    def set_user_channel_setting(self, server_id, channel, nickname,
            setting, value):
        self.execute(
            """INSERT OR REPLACE INTO user_channel_settings VALUES
            (?, ?, ?, ?, ?)""",
            [server_id, channel.lower(), nickname.lower(), setting.lower(),
            json.dumps(value)])
    def get_user_channel_setting(self, server_id, channel, nickname,
            setting, default=None):
        value = self.execute_fetchone(
            """SELECT value FROM user_channel_settings WHERE
            server_id=? AND channel=? AND nickname=? and setting=?""",
            [server_id, channel.lower(), nickname.lower(), setting.lower()])
        if value:
            return json.loads(value[0])
        return default
    def find_user_channel_settings(self, server_id, channel, nickname,
            pattern, default=[]):
        values = self.execute_fetchall(
            """SELECT setting, value FROM user_channel_settings WHERE
            server_id=? AND channel=? AND nickname=? AND setting LIKE '?'""",
            [server_id, channel.lower(), nickname.lower(), pattern.lower()])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def find_user_channel_settings_prefix(self, server_id, channel, nickname,
            prefix, default=[]):
        return self.find_user_settings(server_id, nickname, "%s%" % prefix,
            default)
    def get_user_channel_settings_per_setting(self, server_id, nickname,
            setting, default=[]):
        values = self.execute_fetchall(
            """SELECT channel, value FROM user_channel_settings WHERE
            server_id=? AND nickname=? AND setting=?""",
            [server_id, nickname.lower(), setting])
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def del_user_channel_setting(self, server_id, channel, nickname, setting):
        self.execute(
            """DELETE FROM user_channel_settings WHERE
            server_id=? AND channel=? AND nickname=? AND setting=?""",
            [server_id, channel.lower(), nickname.lower(), setting.lower()])

