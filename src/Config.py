import configparser, os

class Config(object):
    def __init__(self, location):
        self.location = location
        self._config = {}
        self.load()

    def load(self):
        if os.path.isfile(self.location):
            with open(self.location) as config_file:
                parser = configparser.ConfigParser()
                parser.read_string(config_file.read())
                self._config = dict(parser["bot"].items())

    def __getitem__(self, key):
        return self._config[key]
    def get(self, key, default=None):
        return self._config.get(key, default)
    def __contains__(self, key):
        return key in self.config

