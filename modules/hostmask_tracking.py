from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("new.user")
    def new_user(self, event):
        userhost = event["user"].userhost()
        if not userhost == None:
            known_hostmasks = event["user"].get_setting("known-hostmasks", [])
            if not userhost in known_hostmasks:
                known_hostmasks.append(userhost)
                event["user"].set_setting("known-hostmasks", known_hostmasks)
