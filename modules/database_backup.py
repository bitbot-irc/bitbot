import datetime, glob, os, shutil, time
from src import Utils

BACKUP_INTERVAL = 60*60 # 1 hour
BACKUP_COUNT = 5

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        now = datetime.datetime.now()
        until_next_hour = 60-now.second
        until_next_hour += ((60-(now.minute+1))*60)

        bot.timers.add("database-backup", BACKUP_INTERVAL,
            time.time()+until_next_hour)

    @Utils.hook("timer.database-backup")
    def backup(self, event):
        location =  self.bot.database.location
        files = glob.glob("%s.*" % location)
        files = sorted(files)

        if len(files) == 5:
            os.remove(files[0])

        suffix = datetime.datetime.now().strftime("%y-%m-%d.%H:%M:%S")
        backup_file = "%s.%s" % (location, suffix)
        shutil.copy2(location, backup_file)

        event["timer"].redo()
