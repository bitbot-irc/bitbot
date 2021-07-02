from src import ModuleManager, utils
import datetime

class Module(ModuleManager.BaseModule):
    _name = "beat"


    @utils.hook("received.command.beat")
    @utils.kwarg("help","Gives the current .beat time")
    def beat(self, event):
        now = datetime.datetime.utcnow()
        hour = (now.hour+1)%24
        minutes = now.minute
        seconds = now.second
        beat_time = ((hours*3600)+(minutes*60)+seconds)/86.4
        event["stdout"].write("The current time is @%0.2f." % (beat_time))
