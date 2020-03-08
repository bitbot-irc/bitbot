import urllib.parse
from src import ModuleManager, utils

def _parse(s):
    parsed = urllib.parse.urlparse(s)
    return urllib.parse.urljoin(s, parsed.path), parsed.query

SETTING = utils.FunctionSetting(_parse, "yourls",
    "Set YOURLS server (and token) to use for URL shortening",
    example="https://bitbot.dev/yourls-api.php?1002a612b4",
    format=utils.sensitive_format)

@utils.export("botset", SETTING)
@utils.export("serverset", SETTING)
@utils.export("channelset", SETTING)
class Module(ModuleManager.BaseModule):
    @utils.export("shorturl-x-yourls")
    def _shorturl(self, server, context, url):
        if len(url) < 20:
            return None

        setting = server.get_setting("yourls",
            self.bot.get_setting("yourls", None))
        if context:
            setting = context.get_setting("yourls", setting)

        if not setting == None:
            url, token = setting

            page = utils.http.request(URL, post_data={
                "signature": token,
                "action": "shorturl",
                "url": url,
                "format": "json"}).json()
            if page:
                return page["shorturl"]
            return None
