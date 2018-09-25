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
        full_location =  self.bot.database.full_location
        files = glob.glob("%s.*" % full_location)
        files = sorted(files)

        if len(files) == 5:
            os.remove(files[0])

        suffix = datetime.datetime.now().strftime("%y-%m-%d.%H:%M:%S")
        backup_file = "%s.%s" % (full_location, suffix)
        shutil.copy2(full_location, backup_file)

        event["timer"].redo()
