#--require-config virustotal-api-key

import re
import Utils

URL_VIRUSTOTAL = "https://www.virustotal.com/vtapi/v2/url/report"
RE_URL = re.compile(r"https?://\S+", re.I)

class Module(object):
    def __init__(self, bot, events):
        self.bot = bot
        self.events = events
        events.on("received.message.channel").hook(self.message)
        events.on("postboot").on("configure").on(
            "channelset").assure_call(setting="check-urls",
            help="Enable/Disable automatically checking for malicious urls",
            validate=Utils.bool_or_none)

    def message(self, event):
        match = RE_URL.search(event["message"])
        if match and event["channel"].get_setting("check-urls",
                event["server"].get_setting("check-urls", False)):
            url = match.group(0)
            page = Utils.get_url(URL_VIRUSTOTAL, get_params={
                "apikey": self.bot.config["virustotal-api-key"],
                "resource": url}, json=True)

            if page:
                if page.get("positives", 0) > 1:
                    self.events.on("send.stdout").call(
                        module_name="CheckURL", target=event["channel"],
                        message="%s just send a malicous URL!" %
                        event["user"].nickname)

