import json, os, sqlite3, threading

class Database(object):
    def __init__(self, bot, location="bot.db"):
        self.location = location
        self.full_location = os.path.join(bot.bot_directory,
            self.location)
        self.database = sqlite3.connect(self.full_location,
            check_same_thread=False, isolation_level=None)
        self.database.execute("PRAGMA foreign_keys")
        self.cursors = {}

        self.make_servers_table()
        self.make_bot_settings_table()
        self.make_server_settings_table()
        self.make_channel_settings_table()
        self.make_user_settings_table()

    def cursor(self):
        id = threading.current_thread().ident
        if not id in self.cursors:
            self.cursors[id] = self.database.cursor()
        return self.cursors[id]

    def make_servers_table(self):
        try:
            self.cursor().execute("""CREATE TABLE servers
                (server_id INTEGER PRIMARY KEY,
                hostname TEXT, port INTEGER, password TEXT,
                ipv4 BOOLEAN, tls BOOLEAN, nickname TEXT,
                username TEXT, realname TEXT)""")
        except sqlite3.Error as e:
            pass
    def make_bot_settings_table(self):
        try:
            self.cursor().execute("""CREATE TABLE bot_settings
                (setting TEXT PRIMARY KEY, value TEXT)""")
        except sqlite3.Error as e:
            pass
    def make_server_settings_table(self):
        try:
            self.cursor().execute("""CREATE TABLE server_settings
                (server_id INTEGER, setting TEXT, value TEXT,
                FOREIGN KEY(server_id) REFERENCES
                servers(server_id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, setting))""")
        except sqlite3.Error as e:
            pass
    def make_channel_settings_table(self):
        try:
            self.cursor().execute("""CREATE TABLE channel_settings
                (server_id INTEGER, channel TEXT, setting TEXT,
                value TEXT, FOREIGN KEY (server_id) REFERENCES
                servers(server_id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, channel, setting))""")
        except sqlite3.Error as e:
            pass
    def make_user_settings_table(self):
        try:
            self.cursor().execute("""CREATE TABLE user_settings
                (server_id INTEGER, nickname TEXT, setting TEXT,
                value TEXT, FOREIGN KEY (server_id) REFERENCES
                servers(server_id) ON DELETE CASCADE,
                PRIMARY KEY (server_id, nickname, setting))""")
        except sqlite3.Error as e:
            pass

    def set_bot_setting(self, setting, value):
        self.cursor().execute("""INSERT OR REPLACE INTO bot_settings
            VALUES (?, ?)""", [setting.lower(), json.dumps(value)])
    def get_bot_setting(self, setting, default=None):
        self.cursor().execute("""SELECT value FROM bot_settings
            WHERE setting=?""", [setting.lower()])
        value = self.cursor().fetchone()
        if value:
            return json.loads(value[0])
        return default
    def find_bot_settings(self, pattern, default=[]):
        self.cursor().execute("""SELECT setting, value FROM bot_settings
            WHERE setting LIKE ?""", [pattern.lower()])
        values = self.cursor().fetchall()
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def del_bot_setting(self, setting):
        self.cursor().execute("""DELETE FROM bot_settings WHERE
            setting=?""", [setting.lower()])

    def set_server_setting(self, server_id, setting, value):
        self.cursor().execute("""INSERT OR REPLACE INTO server_settings
            VALUES (?, ?, ?)""", [server_id, setting.lower(),
            json.dumps(value)])
    def get_server_setting(self, server_id, setting, default=None):
        self.cursor().execute("""SELECT value FROM server_settings
            WHERE server_id=? AND setting=?""", [server_id,
            setting.lower()])
        value = self.cursor().fetchone()
        if value:
            return json.loads(value[0])
        return default
    def find_server_settings(self, server_id, pattern, default=[]):
        self.cursor().execute("""SELECT setting, value FROM server_settings
            WHERE server_id=? AND setting LIKE ?""", [server_id,
            pattern.lower()])
        values = self.cursor().fetchall()
        if values:
            for i, value in enumerate(values):
                values[i] = value[0], json.loads(value[1])
            return values
        return default
    def del_server_setting(self, server_id, setting):
        self.cursor().execute("""DELETE FROM server_settings WHERE
            server_id=? AND setting=?""", [server_id, setting.lower()])

    def set_channel_setting(self, server_id, channel, setting, value):
        self.cursor().execute("""INSERT OR REPLACE INTO channel_settings
            VALUES (?, ?, ?, ?)""", [server_id, channel.lower(),
            setting.lower(), json.dumps(value)])
    def get_channel_setting(self, server_id, channel, setting, default=None):
        self.cursor().execute("""SELECT value FROM channel_settings
            WHERE server_id=? AND channel=? AND setting=?""",
            [server_id, channel.lower(), setting.lower()])
        value = self.cursor().fetchone()
        if value:
            return json.loads(value[0])
        return default
    def find_channel_settings(self, server_id, channel, pattern, default=[]):
        self.cursor().execute("""SELECT setting, value FROM channel_settings
            WHERE server_id=? AND channel=? setting LIKE '?'""", [server_id,
            channel.lower(), pattern.lower()])
        values = self.cursor().fetchall()
        if values:
            for i, value in enumerate(values):
                values[i] = json.loads(value)
            return values
        return default
    def del_channel_setting(self, server_id, channel, setting):
        self.cursor().execute("""DELETE FROM channel_settings WHERE
            server_id=? AND channel=? AND setting=?""", [server_id,
            channel.lower(), setting.lower()])

    def set_user_setting(self, server_id, nickname, setting, value):
        self.cursor().execute("""INSERT OR REPLACE INTO user_settings
            VALUES (?, ?, ?, ?)""", [server_id, nickname.lower(),
            setting.lower(), json.dumps(value)])
    def get_user_setting(self, server_id, nickname, setting, default=None):
        self.cursor().execute("""SELECT value FROM user_settings
            WHERE server_id=? AND nickname=? and setting=?""",
            [server_id, nickname.lower(), setting.lower()])
        value = self.cursor().fetchone()
        if value:
            return json.loads(value[0])
        return default
    def find_user_settings(self, server_id, nickname, pattern, default=[]):
        self.cursor().execute("""SELECT setting, value FROM user_settings
            WHERE server_id=? AND nickname=? setting LIKE '?'""", [server_id,
            nickname.lower(), pattern.lower()])
        values = self.cursor().fetchall()
        if values:
            for i, value in enumerate(values):
                values[i] = json.loads(value)
            return values
        return default
    def del_user_setting(self, server_id, nickname, setting):
        self.cursor().execute("""DELETE FROM user_settings WHERE
            server_id=? AND nickname=? AND setting=?""", [server_id,
            nickname.lower(), setting.lower()])

    def add_server(self, hostname, port, password, ipv4, tls, nickname,
            username=None, realname=None):
        username = username or nickname
        realname = realname or nickname
        self.cursor().execute("""INSERT INTO servers (hostname, port,
            password, ipv4, tls, nickname, username, realname) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?)""", [hostname, port, password, ipv4,
            tls, nickname, username, realname])
    def get_servers(self):
        self.cursor().execute("""SELECT server_id, hostname, port, password,
            ipv4, tls, nickname, username, realname FROM servers""")
        return self.cursor().fetchall()
    def get_server(self, id):
        self.cursor().execute("""SELECT server_id, hostname, port, password,
            ipv4, tls, nickname, username, realname FROM servers WHERE
            server_id=?""", [id])
        return self.cursor().fetchone()
