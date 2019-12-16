#--require-config healthcheck-url

from bitbot import ModuleManager, utils

# this module was created for use with https://healthchecks.io/
# but it can be used for any similar URL-pinging service.

class Module(ModuleManager.BaseModule):
    @utils.hook("cron")
    @utils.kwarg("schedule", "*/10")
    def ten_minutes(self, event):
        utils.http.request(self.bot.config["healthcheck-url"])
