import enum, queue, os, select, socket, threading, time, traceback, typing, uuid
from src import EventManager, Exports, IRCServer, Logging, ModuleManager
from src import Socket, utils

VERSION = "v1.7.1"
SOURCE = "https://git.io/bitbot"

class TriggerResult(enum.Enum):
    Return = 1
    Exception = 2

class Bot(object):
    def __init__(self, directory, args, cache, config, database, events,
            exports, log, modules, timers):
        self.directory = directory
        self.args = args
        self.cache = cache
        self.config = config
        self.database = database
        self._events = events
        self._exports = exports
        self.log = log
        self.modules = modules
        self._timers = timers

        self.start_time = time.time()
        self.lock = threading.Lock()
        self.running = True
        self.poll = select.epoll()

        self.servers = {}
        self.other_sockets = {}
        self._trigger_server, self._trigger_client = socket.socketpair()
        self.add_socket(Socket.Socket(self._trigger_server, lambda _, s: None))

        self._trigger_functions = []
        self._events.on("timer.reconnect").hook(self._timed_reconnect)

    def trigger(self,
            func: typing.Optional[typing.Callable[[], typing.Any]]=None
            ) -> typing.Any:
        func = func or (lambda: None)

        if utils.is_main_thread():
            returned = func()
            self._trigger_client.send(b"TRIGGER")
            return returned

        self.lock.acquire()

        func_queue = queue.Queue(1) # type: queue.Queue[str]
        self._trigger_functions.append([func, func_queue])

        self.lock.release()
        self._trigger_client.send(b"TRIGGER")

        type, returned = func_queue.get(block=True)
        if type == TriggerResult.Exception:
            raise returned
        elif type == TriggerResult.Return:
            return returned

    def load_modules(self, safe: bool=False
            ) -> typing.Tuple[typing.List[str], typing.List[str]]:
        db_blacklist = set(self.get_setting("module-blacklist", []))
        db_whitelist = set(self.get_setting("module-whitelist", []))

        conf_blacklist = self.config.get("module-blacklist", "").split(",")
        conf_whitelist = self.config.get("module-whitelist", "").split(",")

        conf_blacklist = set(filter(None, conf_blacklist))
        conf_whitelist = set(filter(None, conf_whitelist))

        blacklist = db_blacklist|conf_blacklist
        whitelist = db_whitelist|conf_whitelist

        return self.modules.load_modules(self, whitelist=whitelist,
            blacklist=blacklist, safe=safe)

    def add_server(self, server_id: int, connect: bool = True,
            connection_param_args: typing.Dict[str, str]={}
            ) -> IRCServer.Server:
        connection_params = utils.irc.IRCConnectionParameters(
            *self.database.servers.get(server_id))
        connection_params.args = connection_param_args

        new_server = IRCServer.Server(self, self._events,
            connection_params.id, connection_params.alias, connection_params)
        self._events.on("new.server").call(server=new_server)

        if not connect:
            return new_server

        self.connect(new_server)

        return new_server

    def add_socket(self, sock: socket.socket):
        self.other_sockets[sock.fileno()] = sock
        self.poll.register(sock.fileno(), select.EPOLLIN)

    def remove_socket(self, sock: socket.socket):
        del self.other_sockets[sock.fileno()]
        self.poll.unregister(sock.fileno())

    def get_server_by_id(self, id: int) -> typing.Optional[IRCServer.Server]:
        for server in self.servers.values():
            if server.id == id:
                return server
        return None
    def get_server_by_alias(self, alias: str) -> typing.Optional[IRCServer.Server]:
        alias_lower = alias.lower()
        for server in self.servers.values():
            if server.alias.lower() == alias_lower:
                return server
        return None

    def connect(self, server: IRCServer.Server) -> bool:
        try:
            server.connect()
        except Exception as e:
            self.log.warn("Failed to connect to %s: %s",
                [str(server), str(e)])
            return False
        self.servers[server.fileno()] = server
        self.poll.register(server.fileno(), select.EPOLLOUT)
        return True

    def next_send(self) -> typing.Optional[float]:
        next = None
        for server in self.servers.values():
            timeout = server.socket.send_throttle_timeout()
            if (server.socket.waiting_send() and
                    (next == None or timeout < next)):
                next = timeout
        return next

    def next_ping(self) -> typing.Optional[float]:
        timeouts = []
        for server in self.servers.values():
            timeout = server.until_next_ping()
            if not timeout == None:
                timeouts.append(timeout)
        if not timeouts:
            return None
        return min(timeouts)

    def next_read_timeout(self) -> typing.Optional[float]:
        timeouts = []
        for server in self.servers.values():
            timeouts.append(server.until_read_timeout())
        if not timeouts:
            return None
        return min(timeouts)

    def get_poll_timeout(self) -> float:
        timeouts = []
        timeouts.append(self._timers.next())
        timeouts.append(self.next_send())
        timeouts.append(self.next_ping())
        timeouts.append(self.next_read_timeout())
        timeouts.append(self.cache.next_expiration())
        return min([timeout for timeout in timeouts if not timeout == None])

    def register_read(self, server: IRCServer.Server):
        self.poll.modify(server.fileno(), select.EPOLLIN)
    def register_write(self, server: IRCServer.Server):
        self.poll.modify(server.fileno(), select.EPOLLOUT)
    def register_both(self, server: IRCServer.Server):
        self.poll.modify(server.fileno(),
            select.EPOLLIN|select.EPOLLOUT)

    def disconnect(self, server: IRCServer.Server):
        try:
            self.poll.unregister(server.fileno())
        except FileNotFoundError:
            pass
        del self.servers[server.fileno()]

    def _timed_reconnect(self, event: EventManager.Event):
        if not self.reconnect(event["server_id"],
                event.get("connection_params", None)):
            event["timer"].redo()
    def reconnect(self, server_id: int, connection_params: typing.Optional[
            utils.irc.IRCConnectionParameters]=None) -> bool:
        args = {} # type: typing.Dict[str, str]
        if not connection_params == None:
            args = typing.cast(utils.irc.IRCConnectionParameters,
                connection_params).args

        server = self.add_server(server_id, False, args)
        if self.connect(server):
            self.servers[server.fileno()] = server
            return True
        return False

    def set_setting(self, setting: str, value: typing.Any):
        self.database.bot_settings.set(setting, value)
    def get_setting(self, setting: str, default: typing.Any=None) -> typing.Any:
        return self.database.bot_settings.get(setting, default)
    def find_settings(self, pattern: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.database.bot_settings.find(pattern, default)
    def find_settings_prefix(self, prefix: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.database.bot_settings.find_prefix(
            prefix, default)
    def del_setting(self, setting: str):
        self.database.bot_settings.delete(setting)

    def run(self):
        while self.running:
            if not self.servers:
                break

            events = self.poll.poll(self.get_poll_timeout())
            self.lock.acquire()
            self._timers.call()
            self.cache.expire()

            for func, func_queue in self._trigger_functions:
                try:
                    returned = func()
                    type = TriggerResult.Return
                except Exception as e:
                    returned = e
                    type = TriggerResult.Exception
                func_queue.put([type, returned])
            self._trigger_functions.clear()

            for fd, event in events:
                sock = None
                irc = False
                if fd in self.servers:
                    sock = self.servers[fd]
                    irc = True
                elif fd in self.other_sockets:
                    sock = self.other_sockets[fd]

                if sock:
                    if event & select.EPOLLIN:
                        data = sock.read()
                        if data == None:
                            sock.disconnect()
                            continue

                        for piece in data:
                            sock.parse_data(piece)
                    elif event & select.EPOLLOUT:
                        try:
                            sock._send()
                        except:
                            self.log.error("Failed to write to %s",
                                [str(sock)])
                            raise

                        if sock.fileno() in self.servers:
                            self.register_read(sock)
                    elif event & select.EPULLHUP:
                        self.log.warn("Recieved EPOLLHUP for %s", [str(sock)])
                        sock.disconnect()

            for server in list(self.servers.values()):
                if server.read_timed_out():
                    self.log.warn("Pinged out from %s", [str(server)])
                    server.disconnect()
                elif server.ping_due() and not server.ping_sent:
                    server.send_ping()
                    server.ping_sent = True
                if not server.socket.connected:
                    self._events.on("server.disconnect").call(server=server)
                    self.disconnect(server)

                    if not self.get_server_by_id(server.id):
                        reconnect_delay = self.config.get("reconnect-delay", 10)
                        self._timers.add("reconnect", reconnect_delay,
                            server_id=server.id)
                        self.log.warn(
                            "Disconnected from %s, reconnecting in %d seconds",
                            [str(server), reconnect_delay])
                elif server.socket.waiting_immediate_send() or (
                        server.socket.waiting_send() and
                        server.socket.throttle_done()):
                    self.register_both(server)

            for sock in list(self.other_sockets.values()):
                if not sock.connected:
                    self.remove_socket(sock)
                elif sock.waiting_send():
                    self.register_both(sock)

            self.lock.release()
