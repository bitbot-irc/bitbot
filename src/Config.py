import configparser, os

class Config(object):
    def __init__(self, bot, directory, filename="bot.conf"):
        self.bot = bot
        self.filename = filename
        self.full_location = os.path.join(directory, filename)
        self.bot.config = {}
        self.load_config()

    def load_config(self):
        if os.path.isfile(self.full_location):
            with open(self.full_location) as config_file:
                parser = configparser.ConfigParser()
                parser.read_string(config_file.read())
                return dict(parser["bot"].items())
