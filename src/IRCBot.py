import os, select, socket, sys, threading, time, traceback, typing, uuid
from src import EventManager, Exports, IRCServer, Logging, ModuleManager
from src import Socket, utils

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

    def trigger(self, func: typing.Callable[[], typing.Any]=None):
        self.lock.acquire()
        if func:
            self._trigger_functions.append(func)
        self._trigger_client.send(b"TRIGGER")
        self.lock.release()

    def add_server(self, server_id: int, connect: bool = True,
            connection_params: typing.Optional[
            utils.irc.IRCConnectionParameters]=None) -> IRCServer.Server:
        if not connection_params:
            connection_params = utils.irc.IRCConnectionParameters(
                *self.database.servers.get(server_id))

        new_server = IRCServer.Server(self, self._events,
            connection_params.id, connection_params.alias, connection_params)
        self._events.on("new.server").call(server=new_server)

        if not connect or not new_server.get_setting("connect", True):
            return new_server

        self.connect(new_server)

        return new_server

    def add_socket(self, sock: socket.socket):
        self.other_sockets[sock.fileno()] = sock
        self.poll.register(sock.fileno(), select.EPOLLIN)

    def remove_socket(self, sock: socket.socket):
        del self.other_sockets[sock.fileno()]
        self.poll.unregister(sock.fileno())

    def get_server(self, id: int) -> typing.Optional[IRCServer.Server]:
        for server in self.servers.values():
            if server.id == id:
                return server
        return None

    def connect(self, server: IRCServer.Server) -> bool:
        try:
            server.connect()
        except:
            sys.stderr.write("Failed to connect to %s\n" % str(server))
            traceback.print_exc()
            return False
        self.servers[server.fileno()] = server
        self.poll.register(server.fileno(), select.EPOLLOUT)
        return True

    def next_send(self) -> typing.Optional[float]:
        next = None
        for server in self.servers.values():
            timeout = server.send_throttle_timeout()
            if server.waiting_send() and (next == None or timeout < next):
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
        if not self.reconnect(event["server_id"], event["connection_params"]):
            event["timer"].redo()
    def reconnect(self, server_id: int, connection_params: typing.Optional[
            utils.irc.IRCConnectionParameters]=None) -> bool:
        server = self.add_server(server_id, False, connection_params)
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
            events = self.poll.poll(self.get_poll_timeout())
            self.lock.acquire()
            self._timers.call()
            self.cache.expire()

            for func in self._trigger_functions:
                func()
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
                            if irc:
                                self.log.debug("%s (raw) | %s",
                                    [str(sock), piece])
                            sock.parse_data(piece)
                    elif event & select.EPOLLOUT:
                        sock._send()
                        self.register_read(sock)
                    elif event & select.EPULLHUP:
                        print("hangup")
                        sock.disconnect()

            for server in list(self.servers.values()):
                if server.read_timed_out():
                    print("pingout from %s" % str(server))
                    server.disconnect()
                elif server.ping_due() and not server.ping_sent:
                    server.send_ping()
                    server.ping_sent = True
                if not server.connected:
                    self._events.on("server.disconnect").call(server=server)
                    self.disconnect(server)

                    if not self.get_server(server.id):
                        reconnect_delay = self.config.get("reconnect-delay", 10)
                        self._timers.add("reconnect", reconnect_delay,
                            server_id=server.id,
                            connection_params=server.connection_params)
                        self.log.info(
                            "Disconnected from %s, reconnecting in %d seconds",
                            [str(server), reconnect_delay])
                elif server.waiting_send() and server.throttle_done():
                    self.register_both(server)

            for sock in list(self.other_sockets.values()):
                if not sock.connected:
                    self.remove_socket(sock)
                elif sock.waiting_send():
                    self.register_both(sock)

            self.lock.release()
