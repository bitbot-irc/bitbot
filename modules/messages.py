import re
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.msearch")
    @utils.spec("!-channelonly !<pattern>string")
    def msearch(self, event):
        print(event["spec"])
        pattern = re.compile(event["spec"][0], re.I)
        message_list = list(event["target"].buffer.find_all(pattern))
        message_count = len(message_list)

        if message_list:
            messages = []
            for message in message_list:
                seconds = utils.datetime.seconds_since(message.line.timestamp)
                messages.append("%s ago %s" % (
                    utils.datetime.to_pretty_time(seconds),
                    message.line.format()))

            plural = "message" if message_count == 0 else "messages"
            event["stdout"].write("%s: found %d/%d messages: %s"
                % (event["user"].nickname, message_count,
                len(event["target"].buffer), "\n".join(messages)))
        else:
            event["stderr"].write("%s: no messages found"
                % event["user"].nickname)
