# Used to migrate word stats from prior to v1.19.0
# usage: $ python3 migration/v01.19.00-words.py ~/.bitbot/bot.db

import argparse
parser = argparse.ArgumentParser(description="Migrate pre-v1.19.0 word stats")
parser.add_argument("database")
args = parser.parse_args()

import datetime, sqlite3
database = sqlite3.connect(args.database)
cursor = database.cursor()

cursor.execute(
    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='words'")
if cursor.fetchone()[0] == 0:
    cursor.execute("""
        CREATE TABLE words
        (user_id INTEGER, channel_id INTEGER, date TEXT, count INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
        PRIMARY KEY (user_id, channel_id, date))""")

cursor.execute("SELECT user_id, nickname FROM users")
users = dict(cursor.fetchall())
cursor.execute("SELECT server_id, alias FROM servers")
servers = dict(cursor.fetchall())

channels = {}
cursor.execute("SELECT server_id, channel_id, name FROM channels")
for server_id, channel_id, name in cursor.fetchall():
    channels[channel_id] = (server_id, name)
print(channels)

date = (datetime.datetime.now().date()-datetime.timedelta(days=1)
    ).strftime("%Y-%m-%d")

cursor.execute("""
    SELECT user_id, channel_id, value FROM user_channel_settings
    WHERE setting='words'""")

for user_id, channel_id, count in cursor.fetchall():
    nickname = users[user_id]
    server_id, channel_name = channels[channel_id]

    print("[%s] Migrating %s/%s (%s)" %
        (servers[server_id], channel_name, nickname, count))

    cursor.execute("""
        INSERT INTO words (user_id, channel_id, date, count)
        VALUES (?, ?, ?, ?)""", [user_id, channel_id, date, count])

database.commit()
database.close()

print()
print("Migration successful!")
