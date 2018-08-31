# --ignore
import types, json


def get_target(user):
    return user.alias or user.nickname


def set_setting(user, setting, value):
    target = get_target(user)
    user.bot.database.set_user_setting(user.server.id, target,
                                       setting, value)


def get_setting(user, setting, default=None):
    target = get_target(user)
    return user.bot.database.get_user_setting(user.server.id,
                                              target, setting, default)


def find_settings(user, pattern, default=[]):
    target = get_target(user)
    return user.bot.databse.find_user_settings(user.server.id,
                                               target, pattern, default)


def del_setting(user, setting):
    target = get_target(user)
    user.bot.database.del_user_setting(user.server.id, target,
                                       setting)


class Module(object):
    _name = "Aliases"

    def __init__(self, bot):
        self.bot = bot
        bot.events.on("new").on("user").hook(self.new_user)
        bot.events.on("received").on("nick").hook(self.nickname_change)
        bot.events.on("received").on("command").on("alias").hook(
            self.alias)
        # bot.events.on("received").on("command").on("mainalias").hook(
        #    self.main_alias)

    def new_user(self, event):
        method_type = types.MethodType
        user = event["user"]
        event["user"].alias = user.get_setting("alias")
        if not event["user"].alias:
            event["user"].set_setting("root-alias", True)
        event["user"].set_setting = method_type(set_setting, user)
        event["user"].get_setting = method_type(get_setting, user)
        event["user"].find_settings = method_type(find_settings, user)
        event["user"].del_setting = method_type(del_setting, user)

    def nickname_change(self, event):
        old_nickname = event["old_nickname"]
        new_nickname = event["new_nickname"]
        if not event["user"].alias:
            root_alias = event["user"].get_setting("root-alias", False)
            if not root_alias:
                event["user"].set_setting("alias", old_nickname.lower())
                event["user"].alias = old_nickname.lower()
            else:
                event["user"].alias = None
        elif event["user"].nickname_lower == event["user"].alias:
            event["user"].alias = None

    def _get_aliases(self, target, server):
        return self.bot.database.cursor().execute("""SELECT nickname
            FROM user_settings WHERE setting='alias' AND value=?
            AND server_id=?""", [json.dumps(target.lower()),
                                 server.id]).fetchall()

    def _change_nick(self, old_nickname, new_nickname):
        self.bot.database.cursor().execute("""UPDATE user_settings
            SET nickname=? WHERE nickname=?""", [new_nickname.lower(),
                                                 old_nickname.lower()])

    def alias(self, event):
        if event["args"]:
            target = event["args_split"][0]
        else:
            target = event["user"].nickname
        temp_user = event["server"].get_user(target)
        if temp_user.get_setting("alias"):
            target = temp_user.get_setting("alias")
        aliases = self._get_aliases(target, event["server"])
        if any(aliases):
            event["stdout"].write("Aliases for %s: %s" % (target,
                                                          ", ".join(
                                                              [a[0] for a in
                                                               aliases])))
        else:
            event["stderr"].write("%s has no aliases" % target)

    def main_alias(self, event):
        if event["user"].alias:
            aliases = self._get_aliases(event["user"].alias, event["server"])
            new_alias = event["user"].nickname_lower()
            event["user"].del_setting("alias")
            if any(aliases):
                for nickname in aliases:
                    event["server"].get_user(nickname).set_setting(
                        "alias", alias)
            self._change_nick()
            event["stdout"].write("This nickname has been set as the "
                                  "main alias for it's group of aliases")
        else:
            event["stderr"].write("This nickname is already a main alias")
