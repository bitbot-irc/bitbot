import datetime
from src import ModuleManager, utils

API = "http://worldtimeapi.org/api/timezone/%s"

class Module(ModuleManager.BaseModule):
    _name = "Time"

    @utils.hook("received.command.time")
    def time(self, event):
        """
        :help: Get the time for you or someone else
        :usage: [nickname]
        """
        target_user = event["user"]
        if event["args"]:
            target_user = event["server"].get_user(event["args_split"][0])

        location = target_user.get_setting("location", None)

        if not location == None:
            page = utils.http.request(API % location["timezone"], json=True)

            if page and page.data and not page.data.get("error", None):
                dt = utils.iso8601_parse(page.data["datetime"],
                    microseconds=True)
                human = utils.datetime_human(dt)
                event["stdout"].write("Time for %s: %s" % (target_user.nickname,
                    human))
            else:
                raise utils.EventsResultsError()
        else:
            event["stderr"].write("%s doesn't have a location set" %
                target_user.nickname)
