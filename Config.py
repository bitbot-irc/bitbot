import configparser, os

class Config(object):
    def __init__(self, bot, location="bot.conf"):
        self.bot = bot
        self.location = location
        self.full_location = os.path.join(bot.bot_directory,
            self.location)
        self.bot.config = {}
        self.load_config()

    def load_config(self):
        if os.path.isfile(self.full_location):
            with open(self.full_location) as config_file:
                parser = configparser.ConfigParser()
                parser.read_string(config_file.read())
                self.bot.config = dict(parser["bot"].items())
