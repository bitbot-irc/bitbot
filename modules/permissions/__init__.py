#--depends-on commands
#--depends-on config

import base64, binascii, os
import scrypt
from src import ModuleManager, utils

REQUIRES_IDENTIFY = "You need to be identified to use that command"
REQUIRES_IDENTIFY_INTERNAL = ("You need to be identified to use that command "
 "(/msg %s register | /msg %s identify)")

@utils.export("serverset", {"setting": "identity-mechanism",
    "help": "Set the identity mechanism for this server",
    "example": "ircv3-account"})
class Module(ModuleManager.BaseModule):
    @utils.hook("new.user")
    def new_user(self, event):
        self._logout(event["user"])
        event["user"].admin_master = False

    def _master_password(self):
            master_password = self._random_password()
            hash, salt = self._make_hash(master_password)
            self.bot.set_setting("master-password", [hash, salt])
            return master_password

    def command_line(self, args: str):
        if args == "master-password":
            master_password = self._master_password()
            print("one-time master password: %s" % master_password)
        else:
            raise ValueError("Unknown command-line argument")
    @utils.hook("received.command.masterpassword", private_only=True)
    def master_password(self, event):
        """
        :permission: master-password
        """
        master_password = self._master_password()
        event["stdout"].write("One-time master password: %s" %
            master_password)

    @utils.hook("received.part")
    def on_part(self, event):
        if len(event["user"].channels) == 0 and event["user"
                ].identified_account_override:
            event["user"].send_notice("You no longer share any channels "
                "with me so you have been signed out")

    def _get_hash(self, server, account):
        hash, salt = server.get_user(account).get_setting("authentication",
            (None, None))
        return hash, salt

    def _random_string(self, n):

    def _make_salt(self):
        return base64.b64encode(os.urandom(64)).decode("utf8")

    def _random_password(self):
        return binascii.hexlify(os.urandom(32)).decode("utf8")

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

    @utils.hook("received.command.masterlogin", private_only=True, min_args=1)
    def master_login(self, event):
        saved_hash, saved_salt = self.bot.get_setting("master-password",
            (None, None))

        if saved_hash and saved_salt:
            given_hash, _ = self._make_hash(event["args"], saved_salt)
            if utils.security.constant_time_compare(given_hash, saved_hash):
                self.bot.del_setting("master-password")
                event["user"].admin_master = True
                event["stdout"].write("Master login successful")
                return
        event["stderr"].write("Master login failed")


    @utils.hook("received.command.identify", private_only=True, min_args=1)
    def identify(self, event):
        """
        :help: Identify yourself
        :usage: [account] <password>
        """
        identity_mechanism = event["server"].get_setting("identity-mechanism",
            "internal")
        if not identity_mechanism == "internal":
            raise utils.EventError("The 'identify' command isn't available "
                "on this network")

        if not event["user"].channels:
            raise utils.EventError("You must share at least one channel "
                "with me before you can identify")

        if not event["user"].identified_account_override:
            if len(event["args_split"]) > 1:
                account = event["args_split"][0]
                password = " ".join(event["args_split"][1:])
            else:
                account = event["user"].nickname
                password = event["args"]

            hash, salt = self._get_hash(event["server"], account)
            if hash and salt:
                attempt, _ = self._make_hash(password, salt)
                if utils.security.constant_time_compare(attempt, hash):
                    self._identified(event["server"], event["user"], account)
                    event["stdout"].write("Correct password, you have "
                        "been identified as '%s'." % account)
                    self.events.on("internal.identified").call(
                        user=event["user"])
                else:
                    event["stderr"].write("Incorrect password for '%s'" %
                        account)
            else:
                event["stderr"].write("Account '%s' is not registered" %
                    account)
        else:
            event["stderr"].write("You are already identified")

    @utils.hook("received.command.register", private_only=True, min_args=1)
    def register(self, event):
        """
        :help: Register yourself
        :usage: <password>
        """
        identity_mechanism = event["server"].get_setting("identity-mechanism",
            "internal")
        if not identity_mechanism == "internal":
            raise utils.EventError("The 'identify' command isn't available "
                "on this network")

        hash, salt = self._get_hash(event["server"], event["user"].nickname)
        if not hash and not salt:
            password = event["args"]
            hash, salt = self._make_hash(password)
            event["user"].set_setting("authentication", [hash, salt])
            self._identified(event["server"], event["user"],
                event["user"].nickname)
            event["stdout"].write("Nickname registered successfully")
        else:
            event["stderr"].write("This nickname is already registered")

    @utils.hook("received.command.setpassword", authenticated=True, min_args=1)
    def set_password(self, event):
        """
        :help: Change your password
        :usage: <password>
        """
        hash, salt = self._make_hash(event["args"])
        event["user"].set_setting("authentication", [hash, salt])
        event["stdout"].write("Set your password")

    @utils.hook("received.command.logout", private_only=True)
    def logout(self, event):
        """
        :help: Logout from your identified account
        """
        if event["user"].identified_account_override:
            self._logout(event["user"])
            event["stdout"].write("You have been logged out")
        else:
            event["stderr"].write("You are not logged in")

    @utils.hook("received.command.resetpassword", private_only=True,
        min_args=2)
    def reset_password(self, event):
        """
        :help: Reset a given user's password
        :usage: <nickname> <password>
        :permission: resetpassword
        """
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

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        if event["user"].admin_master:
            return utils.consts.PERMISSION_FORCE_SUCCESS

        permission = event["hook"].get_kwarg("permission", None)
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
            else:
                return utils.consts.PERMISSION_FORCE_SUCCESS
        elif authenticated:
            if not identified_account:
                if identity_mechanism == "internal":
                    return REQUIRES_IDENTIFY_INTERNAL % (
                        event["server"].nickname, event["server"].nickname)
                else:
                    return REQUIRES_IDENTIFY
            else:
                return utils.consts.PERMISSION_FORCE_SUCCESS

    @utils.hook("received.command.mypermissions", authenticated=True)
    def my_permissions(self, event):
        """
        :help: Show your permissions
        """
        permissions = event["user"].get_setting("permissions", [])
        event["stdout"].write("Your permissions: %s" % ", ".join(permissions))

    def _get_user_details(self, server, nickname):
        target = server.get_user(nickname)
        registered = bool(target.get_setting("authentication", None))
        permissions = target.get_setting("permissions", [])
        return [target, registered, permissions]

    @utils.hook("received.command.givepermission", min_args=2)
    def give_permission(self, event):
        """
        :help: Give a given permission to a given user
        :usage: <nickname> <permission>
        :permission: givepermission
        """
        permission = event["args_split"][1].lower()
        target, registered, permissions = self._get_user_details(
            event["server"], event["args_split"][0])

        if target.get_identified_account() == None:
            raise utils.EventError("%s isn't registered" % target.nickname)

        if permission in permissions:
            event["stderr"].write("%s already has permission '%s'" % (
                target.nickname, permission))
        else:
            permissions.append(permission)
            target.set_setting("permissions", permissions)
            event["stdout"].write("Gave permission '%s' to %s" % (
                permission, target.nickname))
    @utils.hook("received.command.removepermission", min_args=2)
    def remove_permission(self, event):
        """
        :help: Remove a given permission from a given user
        :usage: <nickname> <permission>
        :permission: removepermission
        """
        permission = event["args_split"][1].lower()
        target, registered, permissions = self._get_user_details(
            event["server"], event["args_split"][0])

        if target.identified_account == None:
            raise utils.EventError("%s isn't registered" % target.nickname)

        if permission not in permissions:
            event["stderr"].write("%s doesn't have permission '%s'" % (
                target.nickname, permission))
        else:
            permissions.remove(permission)
            if not permissions:
                target.del_setting("permissions")
            else:
                target.set_setting("permissions", permissions)
            event["stdout"].write("Removed permission '%s' from %s" % (
                permission, target.nickname))
