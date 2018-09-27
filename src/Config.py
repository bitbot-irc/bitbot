import configparser, os

class Config(object):
    def __init__(self, location):
        self.location = location

    def load_config(self):
        if os.path.isfile(self.location):
            with open(self.location) as config_file:
                parser = configparser.ConfigParser()
                parser.read_string(config_file.read())
                return dict(parser["bot"].items())
