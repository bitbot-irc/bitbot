#--require-config healthcheck-url

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("cron")
    @utils.kwarg("schedule", "*/10")
    def ten_minutes(self, event):
        utils.http.request(self.bot.config["healthcheck-url"])
