#--depends-on commands
#--depends-on config
#--require-config virustotal-api-key

import re
from src import ModuleManager, utils

URL_VIRUSTOTAL = "https://www.virustotal.com/vtapi/v2/url/report"
RE_URL = re.compile(r"https?://\S+", re.I)

@utils.export("channelset", utils.BoolSetting("check-urls",
    "Enable/Disable automatically checking for malicious URLs"))
@utils.export("serverset", utils.BoolSetting("check-urls",
    "Enable/Disable automatically checking for malicious URLs"))
@utils.export("channelset", utils.BoolSetting("check-urls-kick",
    "Enable/Disable automatically kicking users that send malicious URLs"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel")
    def message(self, event):
        match = RE_URL.search(event["message"])
        if match and event["channel"].get_setting("check-urls",
                event["server"].get_setting("check-urls", False)):
            url = match.group(0)
            page = utils.http.request(URL_VIRUSTOTAL, get_params={
                "apikey": self.bot.config["virustotal-api-key"],
                "resource": url}, json=True)

            if page and page.data.get("positives", 0) > 1:
                if event["channel"].get_setting("check-urls-kick", False):
                    event["channel"].send_kick(event["user"].nickname,
                        "Don't send malicious URLs!")
                else:
                    self.events.on("send.stdout").call(
                        module_name="CheckURL", target=event["channel"],
                        message="%s just send a malicous URL!" %
                        event["user"].nickname, server=event["server"])

