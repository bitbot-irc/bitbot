from src import ModuleManager, utils

SETTING = utils.Setting("ban-format",
    "Set ban format "
    "(${n} = nick, ${u} = username, ${h} = hostname, ${a} = account",
    example="*!${u}@${h}")

@utils.export("channelset", SETTING)
@utils.export("serverset", SETTING)
class Module(ModuleManager.BaseModule):
    def _format_hostmask(self, user, s):
        vars = {}
        vars["n"] = vars["nickname"] = user.nickname
        vars["u"] = vars["username"] = user.username
        vars["h"] = vars["hostname"] = user.hostname
        vars["a"] = vars["account"] = user.account or ""
        return utils.parse.format_token_replace(s, vars)
    @utils.export("ban-mask")
    def banmask(self, server, channel, user):
        format = channel.get_setting("ban-format",
            server.get_setting("ban-format", "*!${u}@${h}"))
        return self._format_hostmask(user, format)

