# Used to migrate karma from prior to v1.16.0
# usage: $ python3 migration/v01.16.00-karma.py ~/.bitbot/bot.db

import argparse
parser = argparse.ArgumentParser(description="Migrate pre-v1.16.0 karma")
parser.add_argument("database")
args = parser.parse_args()

import json, sqlite3
database = sqlite3.connect(args.database)

cursor = database.cursor()
cursor.execute(
    """SELECT server_id, setting, value FROM server_settings
       WHERE setting LIKE 'karma-%'""")
results = cursor.fetchall()

cursor.execute("SELECT nickname, user_id FROM users")
users = dict(cursor.fetchall())

cursor.execute("SELECT server_id, alias FROM servers")
servers = dict(cursor.fetchall())

server_users = {}
for server_id, setting, karma in results:
    if not server_id in server_users:
        cursor.execute(
            "INSERT INTO users (server_id, nickname) VALUES (?, ?)",
            [server_id, "*karma"])
        cursor.execute(
            "SELECT user_id FROM users WHERE server_id=? AND nickname=?",
            [server_id, "*karma"])
        server_users[server_id] = cursor.fetchone()[0]

    print("[%s] Migrating '%s' (%s)" %
        (servers[server_id], setting.replace("karma-", "", 1), karma))
    cursor.execute(
        "INSERT INTO user_settings VALUES (?, ?, ?)",
        [server_users[server_id], setting, karma])

database.commit()
database.close()

print()
print("Migration successful!")
