from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    _name = "Hostmasks"

    @utils.hook("new.user")
    def new_user(self, event):
        userhost = event["user"].userhost()
        if not userhost == None:
            known_hostmasks = event["user"].get_setting("known-hostmasks", [])
            if not userhost in known_hostmasks:
                known_hostmasks.append(userhost)
                event["user"].set_setting("known-hostmasks", known_hostmasks)

    @utils.hook("received.command.maskfind")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Find all nicknames that used a given hostmask")
    @utils.kwarg("usage", "<hostmask>")
    @utils.kwarg("permission", "maskfind")
    def maskfind(self, event):
        all_userhosts = event["server"].get_all_user_settings("known-hostmasks")
        nicknames = set([])
        hostmask_str = event["args_split"][0]
        hostmask = utils.irc.hostmask_parse(hostmask_str)

        searched = 0
        for nickname, userhosts in all_userhosts:
            searched += len(userhosts)
            for userhost in userhosts:
                if hostmask.match(userhost):
                    nicknames.add((nickname, userhost))

        if nicknames:
            outs = []
            for nickname, userhost in sorted(nicknames):
                outs.append("%s (%s)" % (utils.irc.bold(nickname), userhost))
            event["stdout"].write("%s (%d/%d): %s" %
                (hostmask_str, len(nicknames), searched, ", ".join(outs)))
        else:
            event["stderr"].write("Hostmask not found")
