import configparser, os, typing

class Config(object):
    def __init__(self, location: str):
        self.location = location
        self._config = {} # type: typing.Dict[str, str]
        self.load()

    def load(self):
        if os.path.isfile(self.location):
            with open(self.location) as config_file:
                parser = configparser.ConfigParser()
                parser.read_string(config_file.read())
                self._config = {k: v for k, v in parser["bot"].items() if v}

    def __getitem__(self, key: str) -> typing.Any:
        return self._config[key]
    def get(self, key: str, default: typing.Any=None) -> typing.Any:
        return self._config.get(key, default)
    def __contains__(self, key: str) -> bool:
        return key in self._config

