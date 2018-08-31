import base64, os
import scrypt

REQUIRES_IDENTIFY = ("You need to be identified to use that command "
                     "(/msg %s register | /msg %s identify)")


class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("new").on("user").hook(self.new_user)
        bot.events.on("preprocess").on("command").hook(
            self.preprocess_command)
        bot.events.on("received").on("part").hook(self.on_part)
        bot.events.on("received").on("command").on("identify"
                                                   ).hook(self.identify,
                                                          private_only=True,
                                                          min_args=1,
                                                          usage="<password>",
                                                          help="Identify yourself")
        bot.events.on("received").on("command").on("register"
                                                   ).hook(self.register,
                                                          private_only=True,
                                                          min_args=1,
                                                          usage="<password>",
                                                          help="Register your nickname")
        bot.events.on("received.command.logout").hook(self.logout,
                                                      private_only=True,
                                                      help="Sign out from the bot")

        bot.events.on("received.command.mypermissions").hook(
            self.my_permissions, authenticated=True)
        bot.events.on("received.command.givepermission").hook(
            self.give_permission, min_args=2, permission="givepermission")
        bot.events.on("received.command.removepermission").hook(
            self.remove_permission, min_args=2, permission="removepermission")

    def new_user(self, event):
        self._logout(event["user"])

    def on_part(self, event):
        if len(event["user"].channels) == 1 and event["user"].identified:
            event["user"].send_notice("You no longer share any channels "
                                      "with me so you have been signed out")

    def _get_hash(self, user):
        hash, salt = user.get_setting("authentication", (None, None))
        return hash, salt

    def _make_salt(self):
        return base64.b64encode(os.urandom(64)).decode("utf8")

    def _make_hash(self, password, salt=None):
        salt = salt or self._make_salt()
        hash = base64.b64encode(scrypt.hash(password, salt)).decode("utf8")
        return hash, salt

    def _identified(self, user):
        user.identified = True

    def _logout(self, user):
        user.identified = False

    def identify(self, event):
        if not event["user"].channels:
            event["stderr"].write("You must share at least one channel "
                                  "with me before you can identify")
            return
        if not event["user"].identified:
            password = event["args_split"][0]
            hash, salt = self._get_hash(event["user"])
            if hash and salt:
                attempt, _ = self._make_hash(password, salt)
                if attempt == hash:
                    self._identified(event["user"])
                    event["stdout"].write("Correct password, you have "
                                          "been identified.")
                else:
                    event["stderr"].write("Incorrect password")
            else:
                event["stderr"].write("This nickname is not registered")
        else:
            event["stderr"].write("You are already identified")

    def register(self, event):
        hash, salt = self._get_hash(event["user"])
        if not hash and not salt:
            password = event["args_split"][0]
            hash, salt = self._make_hash(password)
            event["user"].set_setting("authentication", [hash, salt])
            self._identified(event["user"])
            event["stdout"].write("Nickname registered successfully")
        else:
            event["stderr"].write("This nickname is already registered")

    def logout(self, event):
        if event["user"].identified:
            self._logout(event["user"])
            event["stdout"].write("You have been logged out")
        else:
            event["stderr"].write("You are not logged in")

    def preprocess_command(self, event):
        authentication = event["user"].get_setting("authentication", None)
        permission = event["hook"].kwargs.get("permission", None)
        authenticated = event["hook"].kwargs.get("authenticated", False)
        protect_registered = event["hook"].kwargs.get("protect_registered",
                                                      False)

        if permission:
            identified = event["user"].identified
            user_permissions = event["user"].get_setting("permissions", [])
            has_permission = permission and (
                    permission in user_permissions or "*" in user_permissions)
            if not identified or not has_permission:
                return "You do not have permission to do that"
        elif authenticated:
            if not event["user"].identified:
                return REQUIRES_IDENTIFY % (event["server"].nickname,
                                            event["server"].nickname)
        elif protect_registered:
            if authentication and not event["user"].identified:
                return REQUIRES_IDENTIFY % (event["server"].nickname,
                                            event["server"].nickname)

    def my_permissions(self, event):
        permissions = event["user"].get_setting("permissions", [])
        event["stdout"].write("Your permissions: %s" % ", ".join(permissions))

    def _get_user_details(self, server, nickname):
        target = server.get_user(nickname)
        registered = bool(target.get_setting("authentication", None))
        permissions = target.get_setting("permissions", [])
        return [target, registered, permissions]

    def give_permission(self, event):
        permission = event["args_split"][1].lower()
        target, registered, permissions = self._get_user_details(
            event["server"], event["args_split"][0])

        if not registered:
            event["stderr"].write("%s isn't registered" % target.nickname)
            return

        if permission in permissions:
            event["stderr"].write("%s already has permission '%s'" % (
                target.nickname, permission))
        else:
            permissions.append(permission)
            target.set_setting("permissions", permissions)
            event["stdout"].write("Gave permission '%s' to %s" % (
                permission, target.nickname))

    def remove_permission(self, event):
        permission = event["args_split"][1].lower()
        target, registered, permissions = self._get_user_details(
            event["server"], event["args_split"][0])

        if not registered:
            event["stderr"].write("%s isn't registered" % target.nickname)
            return

        if not permission in permissions:
            event["stderr"].write("%s already has permission '%s'" % (
                target.nickname, permission))
        else:
            permissions.remove(permission)
            if not permissions:
                target.del_setting("permissions")
            else:
                target.set_setting("permissions", permissions)
            event["stdout"].write("Removed permission '%s' from %s" % (
                permission, target.nickname))
