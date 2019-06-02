#--depends-on msgid

from src import ModuleManager, utils

TAG = utils.irc.MessageTag("msgid", "draft/msgid")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.batch.end")
    def batch_end(self, event):
        if event["batch"].type == "chathistory":
            target_name = event["batch"].args[0]
            if target_name in event["server"].channels:
                target = event["server"].channels.get(target_name)
            else:
                target = event["server"].get_user(target_name)

            last_msgid = target.get_setting("last-msgid", None)
            if not last_msgid == None:
                lines = event["batch"].get_lines()
                stop_index = -1

                for i, line in enumerate(lines):
                    msgid = TAG.get_value(line.tags)
                    if msgid == last_msgid:
                        stop_index = i
                        break

                if not stop_index == -1:
                    return lines[stop_index+1:]
