import datetime
from src import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.message.private").hook(self.private_message)
        exports.add("serverset", {"setting": "ctcp-responses",
            "help": "Set whether I respond to CTCPs on this server",
            "validate": Utils.bool_or_none})

    def private_message(self, event):
        if event["message"][0] == "\x01" and event["message"][-1] == "\x01":
            if event["server"].get_setting("ctcp-responses", True):
                ctcp_command = event["message_split"][0][1:].upper()
                if ctcp_command.endswith("\x01"):
                    ctcp_command = ctcp_command[:-1]
                ctcp_args = " ".join(event["message_split"][1:])[:-1]
                ctcp_args_split = ctcp_args.split(" ")

                ctcp_response = None
                if ctcp_command == "VERSION":
                    ctcp_response = self.bot.config.get("ctcp-version",
                        "BitBot (https://github.com/jesopo/bitbot)")
                elif ctcp_command == "SOURCE":
                    ctcp_response = self.bot.config.get("ctcp-source",
                        "https://github.com/jesopo/bitbot")
                elif ctcp_command == "PING":
                    ctcp_response = " ".join(ctcp_args_split)
                elif ctcp_command == "TIME":
                    ctcp_response = datetime.datetime.now().strftime("%c")

                if ctcp_response:
                    event["user"].send_ctcp_response(ctcp_command,
                        ctcp_response)
