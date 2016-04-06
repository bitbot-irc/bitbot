import base64, os
import scrypt

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("new").on("user").hook(self.new_user)
        bot.events.on("received").on("part").hook(self.on_part)
        bot.events.on("received").on("command").on("identify"
            ).hook(self.identify, private_only=True, min_args=1,
            usage="<password>", help="Identify yourself")
        bot.events.on("received").on("command").on("register"
            ).hook(self.register, private_only=True, min_args=1,
            usage="<password>", help="Register your nickname")
        bot.events.on("received").on("command").on("logout"
            ).hook(self.logout, private_only=True,
            help="Sign out from the bot")

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
        user.permissions = user.get_setting("permissions", [])
    def _logout(self, user):
        user.identified = False
        user.permissions = []
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
