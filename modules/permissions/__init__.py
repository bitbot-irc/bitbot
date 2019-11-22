import base64, binascii, os
import scrypt
from src import ModuleManager, utils

HOSTMASKS_SETTING = "hostmask-account"
NO_PERMISSION = "You do not have permission to do that"

class Module(ModuleManager.BaseModule):
    def on_load(self):
        self.exports.add("is-identified", self._is_identified)
        self.exports.add("account-name", self._account_name)

    @utils.hook("new.server")
    def new_server(self, event):
        hostmasks = {}

        for account, user_hostmasks in event["server"].get_all_user_settings(
                HOSTMASKS_SETTING):
            for hostmask in user_hostmasks:
                hostmasks[hostmask] = account
        event["server"]._hostmasks = hostmasks

    def _make_salt(self):
        return base64.b64encode(os.urandom(64)).decode("utf8")

    def _random_password(self):
        return binascii.hexlify(os.urandom(32)).decode("utf8")

    def _make_hash(self, password, salt=None):
        salt = salt or self._make_salt()
        hash = base64.b64encode(scrypt.hash(password, salt)).decode("utf8")
        return hash, salt

    def _get_hash(self, server, account):
        hash, salt = server.get_user(account).get_setting("authentication",
            (None, None))
        return hash, salt

    def _master_password(self):
        master_password = self._random_password()
        hash, salt = self._make_hash(master_password)
        self.bot.set_setting("master-password", [hash, salt])
        return master_password
    @utils.hook("control.master-password")
    def command_line(self, event):
        master_password = self._master_password()
        return "One-time master password: %s" % master_password

    def _has_identified(self, server, user, account):
        user._id_override = server.get_user_id(account)
    def _is_identified(self, user):
        return not user._id_override == None
    def _signout(self, user):
        user._id_override = None

    def _find_hostmask(self, server, user):
        user_hostmask = user.hostmask()
        for hostmask in server._hostmasks.keys():
            if utils.irc.hostmask_match(user_hostmask, hostmask):
                return (hostmask, server._hostmasks[hostmask])
    def _specific_hostmask(self, server, hostmask, account):
        for user in server.users.values():
            if utils.irc.hostmask_match(user.hostmask(), hostmask):
                if account == None:
                    user._hostmask_account = None
                    self._signout(user)
                else:
                    user._hostmask_account = (hostmask, account)
                    self._has_identified(server, user, account)

    def _account_name(self, user):
        if not user.account == None:
            return user.account
        elif not user._account_override == None:
            return user._account_override
        elif not user._hostmask_account == None:
            return user._hostmask_account[1]

    @utils.hook("new.user")
    def new_user(self, event):
        event["user"]._hostmask_account = None
        event["user"]._account_override = None
        event["user"]._master_admin = False

    def _set_hostmask(self, server, user):
        account = self._find_hostmask(server, user)
        if not account == None:
            hostmask, account = account
            user._hostmask_account = (hostmask, account)
            self._has_identified(server, user, account)

    @utils.hook("received.chghost")
    @utils.hook("received.nick")
    def chghost(self, event):
        if not self._is_identified(event["user"]):
            self._set_hostmask(event["server"], event["user"])
    @utils.hook("received.whox")
    @utils.hook("received.account")
    @utils.hook("received.account.login")
    @utils.hook("received.account.logout")
    @utils.hook("received.join")
    def check_account(self, event):
        if not self._is_identified(event["user"]):
            if event["user"].account:
                self._has_identified(event["server"], event["user"],
                    event["user"].account)
            else:
                self._set_hostmask(event["server"], event["user"])

    def _get_permissions(self, user):
        if self._is_identified(user):
            return user.get_setting("permissions", [])
        return []

    def _has_permission(self, user, permission):
        if user._master_admin:
            return True

        permissions = self._get_permissions(user)
        if permission in permissions:
            return True
        else:
            permission_parts = permission.split(".")
            for user_permission in permissions:
                user_permission_parts = user_permission.split(".")
                for i, part in enumerate(permission_parts):
                    last = i==(len(permission_parts)-1)
                    user_last = i==(len(user_permission_parts)-1)
                    if not permission_parts[i] == user_permission_parts[i]:
                        if user_permission_parts[i] == "*" and user_last:
                            return True
                        else:
                            break
                    else:
                        if last and user_last:
                            return True
        return False

    @utils.hook("received.command.masterlogin")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("private_only", True)
    def master_login(self, event):
        saved_hash, saved_salt = self.bot.get_setting("master-password",
            (None, None))
        if saved_hash and saved_salt:
            given_hash, _ = self._make_hash(event["args"], saved_salt)
            if utils.security.constant_time_compare(given_hash, saved_hash):
                self.bot.del_setting("master-password")
                event["user"]._master_admin = True
                event["stdout"].write("Master login successful")
                return
        event["stderr"].write("Master login failed")

    @utils.hook("received.command.mypermissions")
    @utils.kwarg("authenticated", True)
    def my_permissions(self, event):
        """
        :help: Show your permissions
        """
        permissions = event["user"].get_setting("permissions", [])
        event["stdout"].write("Your permissions: %s" % ", ".join(permissions))


    @utils.hook("received.command.register", private_only=True, min_args=1)
    @utils.kwarg("min_args", 1)
    @utils.kwarg("private_only", True)
    @utils.kwarg("help", "Register your nickname")
    @utils.kwarg("usage", "<password>")
    def register(self, event):
        hash, salt = self._get_hash(event["server"], event["user"].nickname)
        if not hash and not salt:
            password = event["args"]
            hash, salt = self._make_hash(password)
            event["user"].set_setting("authentication", [hash, salt])

            event["user"]._account_override = event["user"].nickname
            self._has_identified(event["server"], event["user"],
                event["user"].nickname)

            event["stdout"].write("Nickname registered successfully")
        else:
            event["stderr"].write("This nickname is already registered")

    @utils.hook("received.command.identify", private_only=True, min_args=1)
    @utils.kwarg("min_args", 1)
    @utils.kwarg("private_only", True)
    @utils.kwarg("help", "Identify for your current nickname")
    @utils.kwarg("usage", "[account] <password>")
    def identify(self, event):
        if not event["user"].channels:
            raise utils.EventError("You must share at least one channel "
                "with me before you can identify")

        if not self._is_identified(event["user"]):
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
                    event["user"]._account_override = account
                    self._has_identified(event["server"], event["user"], account)

                    event["stdout"].write("Correct password, you have "
                        "been identified as %s." % account)
                    self.events.on("internal.identified").call(
                        user=event["user"])
                else:
                    event["stderr"].write("Incorrect password for '%s'" %
                        account)
            else:
                event["stderr"].write("Account '%s' is not registered" %
                    account)
        else:
            event["stderr"].write("You are already identified as %s" %
                self._account_name(event["user"]))

    @utils.hook("received.command.permission")
    @utils.kwarg("min_args", 2)
    @utils.kwarg("usage", "list <account>")
    @utils.kwarg("usage", "clear <account>")
    @utils.kwarg("usage", "add <account> <permission>")
    @utils.kwarg("usage", "remove <account> <permission>")
    @utils.kwarg("permission", "permissions.change")
    def permission(self, event):
        subcommand = event["args_split"][0].lower()
        account = event["args_split"][1]
        target_user = event["server"].get_user(account)

        if subcommand == "list":
            event["stdout"].write("Permissions for %s: %s" % (
                account, ", ".join(self._get_permissions(target_user))))
        elif subcommand == "clear":
            if not self._get_permissions(target_user):
                raise utils.EventError("%s has no permissions" % account)
            target_user.del_setting("permissions")
            event["stdout"].write("Cleared permissions for %s" % account)
        else:
            permissions = event["args_split"][2:]
            if not permissions:
                raise utils.EventError("Please provide at least 1 permission")
            user_permissions = self._get_permissions(target_user)

            if subcommand == "add":
                new = list(set(permissions)-set(user_permissions))
                if not new:
                    raise utils.EventError("No new permissions to give")
                target_user.set_setting("permissions", user_permissions+new)
                event["stdout"].write("Gave %s new permissions: %s" %
                    (account, ", ".join(new)))
            elif subcommand == "remove":
                permissions_set = set(permissions)
                user_permissions_set = set(user_permissions)
                removed = list(user_permissions_set&permissions_set)
                if not (user_permissions_set & permissions_set):
                    raise utils.EventError("New permissions to remove")
                change = list(user_permissions_set - permissions_set)

                if not change:
                    target_user.del_setting("permissions")
                else:
                    target_user.set_setting("permissions", change)
                event["stdout"].write("Removed permissions from %s: %s" %
                    (account, ", ".join(change)))
            else:
                raise utils.EventError("Unknown subcommand %s" % subcommand)

    @utils.hook("received.command.hostmask")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("authenticated", True)
    @utils.kwarg("usage", "list")
    @utils.kwarg("usage", "add [hostmask]")
    @utils.kwarg("usage", "remove [hostmask]")
    def hostmask(self, event):
        subcommand = event["args_split"][0].lower()
        hostmasks = event["user"].get_setting(HOSTMASKS_SETTING, [])

        if subcommand == "list":
            event["stdout"].write("Your hostmasks: %s" % ", ".join(hostmasks))
        else:
            if event["args_split"][1:]:
                hostmask = event["args_split"][1]
            else:
                hostmask = "*!%s" % event["user"].userhost()
            account = self._account_name(event["user"])

            if subcommand == "add":
                if hostmask in hostmasks:
                    raise utils.EventError(
                        "Hostmask %s is already on your account" % hostmask)
                hostmasks.append(hostmask)
                event["user"].set_setting(HOSTMASKS_SETTING, hostmasks)

                self._specific_hostmask(event["server"], hostmask, account)
                event["server"]._hostmasks[hostmask] = account

                event["stdout"].write("Added %s to your hostmasks" % hostmask)
            elif subcommand == "remove":
                if not hostmask in hostmasks:
                    raise utils.EventError("Hostmask %s is not on your account"
                        % hostmask)
                while hostmask in hostmasks:
                    hostmasks.remove(hostmask)
                event["user"].set_setting(HOSTMASKS_SETTING, hostmasks)

                self._specific_hostmask(event["server"], hostmask, None)
                if hostmask in event["server"]._hostmasks:
                    del event["server"]._hostmasks[hostmask]

                event["stdout"].write("Removed %s from your hostmasks"
                    % hostmask)
            else:
                raise utils.EventError("Unknown subcommand %s" % subcommand)

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        allowed = None
        permission = event["hook"].get_kwarg("permission", None)
        authenticated = event["hook"].get_kwarg("authenticated", False)
        if not permission == None:
            allowed = self._has_permission(event["user"], permission)
        elif authenticated:
            allowed = self._is_identified(event["user"])

        if not allowed == None:
            if allowed:
                return utils.consts.PERMISSION_FORCE_SUCCESS, None
            else:
                return utils.consts.PERMISSION_ERROR, NO_PERMISSION
