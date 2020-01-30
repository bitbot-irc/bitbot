import collections, configparser, os, typing

class Config(object):
    def __init__(self, name: str, location: str):
        self._name = name
        self.location = location
        self._config: typing.Dict[str, str] = collections.OrderedDict()

    def _parser(self) -> configparser.ConfigParser:
        return configparser.ConfigParser()

    def load(self):
        if os.path.isfile(self.location):
            with open(self.location) as config_file:
                parser = self._parser()
                parser.read_string(config_file.read())
                self._config.clear()
                for k, v in parser[self._name].items():
                    if v:
                        self._config[k] = v

    def save(self):
        with open(self.location, "w") as config_file:
            parser = self._parser()
            parser[self._name] = self._config.copy()
            parser.write(config_file)

    def __getitem__(self, key: str) -> typing.Any:
        return self._config[key]
    def __setitem__(self, key: str, value: str):
        self._config[key] = value
    def __delitem__(self, key: str):
        self._config.__delitem__(key)
    def __contains__(self, key: str) -> bool:
        return key in self._config

    def get(self, key: str, default: typing.Any=None) -> typing.Any:
        return self._config.get(key, default)

    def get_list(self, key: str):
        if key in self and self[key]:
            return [item.strip() for item in self[key].split(",")]
        return []
    def set_list(self, key: str, list: typing.List[str]):
        value = ",".join(item.strip() for item in list)
        if value:
            self[key] = value
        elif key in self:
            del self[key]
