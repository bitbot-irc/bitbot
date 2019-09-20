import typing
from src import EventManager, IRCBot, IRCChannel, IRCServer, utils

class Channels(object):
    def __init__(self, server: "IRCServer.Server", bot: "IRCBot.Bot",
            events: EventManager.Events):
        self._server = server
        self._bot = bot
        self._events = events
        self._channels = {} # type: typing.Dict[str, IRCChannel.Channel]

    def __iter__(self) -> typing.Iterable[IRCChannel.Channel]:
        return (channel for channel in self._channels.values())
    def __contains__(self, name: str) -> bool:
        return self.contains(name)
    def __len__(self) -> int:
        return len(self._channels)
    def __getitem__(self, name: str):
        return self.get(name)

    def keys(self):
        return self._channels.keys()
    def values(self):
        return self._channels.values()
    def items(self):
        return self._channels.items()

    def get_id(self, channel_name: str, create: bool=True) -> int:
        if create:
            self._bot.database.channels.add(self._server.id, channel_name)
        return self._bot.database.channels.get_id(self._server.id, channel_name)

    def _name_lower(self, channel_name: str) -> str:
        return self._server.irc_lower(channel_name)

    def contains(self, name: str) -> bool:
        return (self._server.is_channel(name) and
            self._name_lower(name) in self._channels)

    def add(self, name: str) -> IRCChannel.Channel:
        id = self.get_id(name)
        lower = self._name_lower(name)
        new_channel = IRCChannel.Channel(lower, id, self._server, self._bot)
        self._channels[lower] = new_channel
        self._events.on("new.channel").call(channel=new_channel, server=self)
        return new_channel

    def remove(self, channel: IRCChannel.Channel):
        lower = self._name_lower(channel.name)
        del self._channels[lower]

    def get(self, name: str):
        return self._channels[self._name_lower(name)]

    def rename(self, old_name, new_name):
        old_lower = self._name_lower(old_name)
        new_lower = self._name_lower(new_name)

        channel = self._channels.pop(old_lower)
        channel.name = new_name
        self._channels[new_name] = channel

        self._bot.database.channels.rename(channel.id, new_lower)
