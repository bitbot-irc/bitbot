import urllib.parse
from src import IRCBot, ModuleManager, utils
from . import ap_actor, ap_server, ap_utils

def _format_username(username, instance):
    return "@%s@%s" % (username, instance)
def _setting_parse(s):
    username, instance = ap_utils.split_username(s)
    if username and instance:
        return _format_username(username, instance)
    return None

@utils.export("botset", utils.FunctionSetting(_setting_parse,
    "fediverse-server", "The bot's local fediverse server username",
    example="@bot@bitbot.dev"))
@utils.export("set", utils.FunctionSetting(_setting_parse, "fediverse",
    help="Set your fediverse account", example="@gargron@mastodon.social"))
class Module(ModuleManager.BaseModule):
    _name = "Fedi"

    def on_load(self):
        server_username = self.bot.get_setting("fediverse-server", None)
        if server_username:
            if not "tls-key" in self.bot.config:
                raise ValueError("`tls-key` not provided in bot config")
            if not "tls-certificate" in self.bot.config:
                raise ValueError("`tls-certificate` not provided in bot config")

            server_username, instance = ap_utils.split_username(server_username)
            self.server = ap_server.Server(self.bot, server_username, instance)

            self.events.on("api.get.ap-webfinger").hook(
                self.server.ap_webfinger, authenticated=False)
            self.events.on("api.get.ap-user").hook(
                self.server.ap_user, authenticated=False)
            self.events.on("api.post.ap-inbox").hook(
                self.server.ap_inbox, authenticated=False)
            self.events.on("api.get.ap-outbox").hook(
                self.server.ap_outbox, authenticated=False)
    def unload(self):
        if not self.server == None:
            self.server.unload()

    @utils.hook("received.command.fediverse")
    @utils.hook("received.command.fedi", alias_of="fediverse")
    @utils.kwarg("help", "Get someone's latest toot")
    @utils.kwarg("usage", "@<user>@<instance>")
    def fedi(self, event):
        account = None
        if not event["args"]:
            account = event["user"].get_setting("fediverse", None)
        elif not "@" in event["args"]:
            target = event["args_split"][0]
            if event["server"].has_user_id(target):
                target_user = event["server"].get_user(target)
                account = target_user.get_setting("fediverse", None)
        else:
            account = event["args_split"][0]

        username = None
        instance = None
        if account:
            username, instance = ap_utils.split_username(account)

        if not username or not instance:
            raise utils.EventError("Please provide @<user>@<instance>")

        actor_url = ap_utils.find_actor(username, instance)

        if not actor_url:
            raise utils.EventError("Failed to find actor")

        actor = ap_actor.Actor(actor_url)
        actor.load()
        items = actor.outbox.load()

        if not items:
            raise utils.EventError("No toots found")

        cw, out, url = ap_utils.format_note(actor, items[0])
        shorturl = self.exports.get_one("shorturl")(event["server"], url,
            context=event["target"])

        if not cw == None:
            out = "CW: %s - %s" % (cw, shorturl)
        else:
            out = "%s - %s" % (out, shorturl)
        event["stdout"].write(out)
