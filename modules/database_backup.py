import datetime, glob, os, shutil, time

BACKUP_INTERVAL = 60*60 # 1 hour
BACKUP_COUNT = 5

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        now = datetime.datetime.now()
        until_next_hour = 60-now.second
        until_next_hour += ((60-(now.minute+1))*60)

        events.on("timer.database-backup").hook(self.backup)
        bot.add_timer("database-backup", BACKUP_INTERVAL, persist=False,
            next_due=time.time()+until_next_hour)

    def backup(self, event):
        files = glob.glob("%s.*" % self.bot.args.database)
        files = sorted(files)

        if len(files) == 5:
            os.remove(files[0])

        suffix = datetime.datetime.now().strftime("%y-%m-%d.%H:%M:%S")
        backup_file = "%s.%s" % (self.bot.args.database, suffix)
        shutil.copy2(self.bot.args.database, backup_file)

        event["timer"].redo()
