import base64, os
import scrypt

REQUIRES_IDENTIFY = ("You need to be identified to use that command "
 "(/msg %s register | /msg %s identify)")

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("new.user").hook(self.new_user)
        events.on("preprocess.command").hook(
            self.preprocess_command)
        events.on("received.part").hook(self.on_part)

        events.on("received").on("command").on("identify"
            ).hook(self.identify, private_only=True, min_args=2,
            usage="<account> <password>", help="Identify yourself")
        events.on("received").on("command").on("register"
            ).hook(self.register, private_only=True, min_args=1,
            usage="<password>", help="Register your nickname")
        events.on("received.command.logout").hook(self.logout,
             private_only=True, help="Sign out from the bot")
        events.on("received.command.resetpassword").hook(
            self.reset_password, private_only=True,
            help="Reset a user's password", min_args=2,
            usage="<nickname> <password>", permission="resetpassword")

        events.on("received.command.mypermissions").hook(
            self.my_permissions, authenticated=True)
        events.on("received.command.givepermission").hook(
            self.give_permission, min_args=2, permission="givepermission")
        events.on("received.command.removepermission").hook(
            self.remove_permission, min_args=2, permission="removepermission")

    def new_user(self, event):
        self._logout(event["user"])

    def on_part(self, event):
        if len(event["user"].channels) == 1 and event["user"
                ].identified_account_override:
            event["user"].send_notice("You no longer share any channels "
                "with me so you have been signed out")

    def _get_hash(self, server, account):
        hash, salt = server.get_user(account).get_setting("authentication",
            (None, None))
        return hash, salt

    def _make_salt(self):
        return base64.b64encode(os.urandom(64)).decode("utf8")

    def _make_hash(self, password, salt=None):
        salt = salt or self._make_salt()
        hash = base64.b64encode(scrypt.hash(password, salt)).decode("utf8")
        return hash, salt

    def _identified(self, server, user, account):
        user.identified_account_override = account
        user.identified_account_id_override = server.get_user(account).get_id()

    def _logout(self, user):
        user.identified_account_override = None
        user.identified_account_id_override = None

    def identify(self, event):
        identity_mechanism = event["server"].get_setting("identity-mechanism",
            "internal")
        if not identity_mechanism == "internal":
            event["stderr"].write("The 'identify' command isn't available "
                "on this network")
            return

        if not event["user"].channels:
            event["stderr"].write("You must share at least one channel "
                "with me before you can identify")
            return

        if not event["user"].identified_account_override:
            account = event["args_split"][0]
            password = " ".join(event["args_split"][1:])
            hash, salt = self._get_hash(event["server"], account)
            if hash and salt:
                attempt, _ = self._make_hash(password, salt)
                if attempt == hash:
                    self._identified(event["server"], event["user"], account)
                    event["stdout"].write("Correct password, you have "
                        "been identified as '%s'." % account)
                else:
                    event["stderr"].write("Incorrect password for '%s'" %
                        account)
            else:
                event["stderr"].write("Account '%s' is not registered" %
                    account)
        else:
            event["stderr"].write("You are already identified")

    def register(self, event):
        identity_mechanism = event["server"].get_setting("identity-mechanism",
            "internal")
        if not identity_mechanism == "internal":
            event["stderr"].write("The 'identify' command isn't available "
                "on this network")
            return

        hash, salt = self._get_hash(event["server"], event["user"].nickname)
        if not hash and not salt:
            password = event["args_split"][0]
            hash, salt = self._make_hash(password)
            event["user"].set_setting("authentication", [hash, salt])
            self._identified(event["server"], event["user"],
                event["user"].nickname)
            event["stdout"].write("Nickname registered successfully")
        else:
            event["stderr"].write("This nickname is already registered")

    def logout(self, event):
        if event["user"].identified_account_override:
            self._logout(event["user"])
            event["stdout"].write("You have been logged out")
        else:
            event["stderr"].write("You are not logged in")

    def reset_password(self, event):
        target = event["server"].get_user(event["args_split"][0])
        password = " ".join(event["args_split"][1:])
        registered = target.get_setting("authentication", None)

        if registered == None:
            event["stderr"].write("'%s' isn't registered" % target.nickname)
        else:
            hash, salt = self._make_hash(password)
            target.set_setting("authentication", [hash, salt])
            event["stdout"].write("Reset password for '%s'" %
                target.nickname)

    def preprocess_command(self, event):
        permission = event["hook"].kwargs.get("permission", None)
        authenticated = event["hook"].kwargs.get("authenticated", False)

        identity_mechanism = event["server"].get_setting("identity-mechanism",
            "internal")
        identified_account = None
        if identity_mechanism == "internal":
            identified_account = event["user"].identified_account_override
        elif identity_mechanism == "ircv3-account":
            identified_account = (event["user"].identified_account or
                event["tags"].get("account", None))

        identified_user = None
        permissions = []
        if identified_account:
            identified_user = event["server"].get_user(identified_account)
            permissions = identified_user.get_setting("permissions", [])

        if permission:
            has_permission = permission and (
                permission in permissions or "*" in permissions)
            if not identified_account or not has_permission:
                return "You do not have permission to do that"
        elif authenticated:
            if not identified_account:
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
