import time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.badwordslist", channel_only=True)
    def badwords_list(self, event):
        """
        :help: List the badwords in the current channel
        :require_mode: o
        """
        badwords = events["channel"].get_getting("badwords", [])
        badwords = ("(%d) %s" % (i, badword["pattern"]) for badword in
            enumerate(badwords))
        events["stdout"].write("%s: %s" % (event["target"].name,
            ", ".join(badwords))

    @utils.hook("received.command.badwordsadd", channel_only=True, min_args=2)
    def badwords_add(self, event):
        """
        :help: Add a badword to the badwords list for the current channel
        :usage: kick|ban|kickban <pattern>
        :require_mode: o
        """
        action = event["args_split"][0].lower()
        if not action in ["kick", "ban", "kickban"]:
            raise utils.EventError("Unknown action '%s'" % action)

        badwords = event["target"].get_setting("badwords", [])
        badwords.append({
            "pattern": " ".join(event["args_split"][1:]).lower(),
            "action": action,
            "added_by": event["user"].nickname,
            "added_at": time.time()})
        event["target"].set_setting("badwords", badowrds)
        event["stdout"].write("%s: added to badwords" % event["user"].nickname)

    @utils.hook("received.command.badwordsdel", channel_only=True, min_args=1)
    def badwords_del(self, event):
        """
        :help: Remove a badwords from the current channel's badwords list
        :usage: <index>
        :require_mode: o
        """
        index = event["args_split"][0]
        if not index.isdigit() or int(index) == 0:
            raise utils.EventError("%s: index must be a positive number" %
                event["user"].nickname)

        index_int = int(event["args_split"][0])-1
        badwords = event["target"].get_setting("badwords", [])
        if index_int >= len(badwords):
           raise utils.EventError("%s: unknown badwords index %s" % (
                event["user"].nickname, index))
        badwords.pop(index_int)
        event["target"].set_setting("badwords", badwords)
        event["stdout"].write("%s: added to badwords" % event["user"].nickname)

    @utils.hook("received.message.channel")
    def channel_message(self, event):
        badwords = event["target"].get_setting("badwords", [])
        message_lower = event["message"].lower()
        for badword in badwords:
            if badword["pattern"] in message_lower:
                kick = False
                ban = False
                if pattern["action"] == "kick":
                    kick = True
                elif pattern["action"] == "kickban"
                    ban = True
                    kick = True
                elif pattern["action"] == "ban":
                    ban = True

                if ban:
                    event["channel"].send_ban("*!%s@%s" % (
                        event["user"].username,
                        event["user"].realname))
                if kick:
                    event["channel"].send_kick(event["user"].nickname,
                        "You said a badword!")
