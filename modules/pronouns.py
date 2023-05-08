#--depends-on commands
#--depends-on config

from src import ModuleManager, utils

@utils.export("set", utils.Setting("pronouns", "Set your pronouns",
    example="they/them"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.pronouns")
    def pronouns(self, event):
        """
        :help: Get your, or someone else's, pronouns
        :usage: [nickname]
        :require_setting: pronouns
        :require_setting_unless: 1
        """
        target_user = event["user"]
        if event["args"]:
            target_user = event["server"].get_user(event["args_split"][0])

        pronouns = target_user.get_setting("pronouns", None)

        if not pronouns == None:
            event["stdout"].write("Pronouns for %s: %s" %
                (target_user.nickname, pronouns))
        else:
            event["stderr"].write("No pronouns set for %s" %
                target_user.nickname)
