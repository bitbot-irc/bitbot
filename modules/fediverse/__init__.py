#--depends-on rest_api

import urllib.parse
from src import IRCBot, ModuleManager, utils
from . import ap_actor, ap_security, ap_server, ap_utils

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
            self.server = ap_server.Server(self.bot, self.exports,
                server_username, instance)

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
    @utils.kwarg("usage", "@<user>@<instance> [!]")
    def fedi(self, event):
        account = None
        url = None

        strict_cw = True
        args_split = event["args_split"][:]
        for i, arg in enumerate(args_split):
            if arg == "!":
                strict_cw = False
                args_split.pop(i)
                break

        if not args_split:
            account = event["user"].get_setting("fediverse", None)
        elif utils.http.REGEX_URL.match(args_split[0]):
            url = args_split[0]
        elif not "@" in args_split[0]:
            target = args_split[0]
            if event["server"].has_user_id(target):
                target_user = event["server"].get_user(target)
                account = target_user.get_setting("fediverse", None)
        else:
            account = args_split[0]

        note = None
        type = "Create"
        if not url == None:
            note_page = ap_utils.activity_request(url)
            if not note_page.content_type in ap_utils.AP_TYPES:
                raise utils.EventError("That's not a fediverse URL")

            note = note_page.json()
            actor = ap_actor.Actor(note["attributedTo"])
            actor.load()
        else:
            username = None
            instance = None
            if account:
                username, instance = ap_utils.split_username(account)

            if not username or not instance:
                raise utils.EventError("Please provide @<user>@<instance>")
            actor, note = self._get_from_outbox(username, instance)
            type = note["type"]
            note = note["object"]

        cw, author, content, url = ap_utils.parse_note(actor, note, type)
        shorturl = self.exports.get("shorturl")(event["server"], url,
            context=event["target"])

        if cw:
            if strict_cw:
                out = "%s: CW %s - %s" % (author, cw, shorturl)
            else:
                out = "(CW %s) %s: %s - %s" % (cw, author, content, shorturl)
        else:
            out = "%s: %s - %s" % (author, content, shorturl)
        event["stdout"].write(out)

    def _get_from_outbox(self, username, instance):
        try:
            actor_url = ap_utils.find_actor(username, instance)
        except ap_utils.FindActorException as e:
            raise utils.EventError(str(e))

        actor = ap_actor.Actor(actor_url)
        if not actor.load():
            raise utils.EventError("Failed to load user")

        items = actor.outbox.load()
        nonreply = [actor.followers]
        first_item = None
        for item in items:
            if (item["type"] == "Announce" or
                    not "cc" in item["object"] or
                    item["object"]["cc"] == nonreply):
                first_item = item
                break

        if not first_item:
            raise utils.EventError("No toots found")

        return actor, first_item
