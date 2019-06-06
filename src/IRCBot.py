import enum, queue, os, queue, select, socket, threading, time, traceback
import typing, uuid
from src import EventManager, Exports, IRCServer, Logging, ModuleManager
from src import Socket, utils

VERSION = "v1.8.0"
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
        self.running = True
        self.servers = {}

        self._event_queue = queue.Queue()

        self._read_poll = select.epoll()
        self._write_poll = select.epoll()

        self._rtrigger_server, self._rtrigger_client = socket.socketpair()
        self._read_poll.register(self._rtrigger_server.fileno(), select.EPOLLIN)

        self._wtrigger_server, self._wtrigger_client = socket.socketpair()
        self._write_poll.register(self._wtrigger_server.fileno(),
            select.EPOLLIN)

        self._rtrigger_lock = threading.Lock()
        self._rtriggered = False
        self._wtrigger_lock = threading.Lock()
        self._wtriggered = False

        self._read_thread = None
        self._write_thread = None

        self._trigger_functions = []
        self._events.on("timer.reconnect").hook(self._timed_reconnect)

    def _trigger_both(self):
        self.trigger_read()
        self.trigger_write()
    def trigger_read(self):
        with self._rtrigger_lock:
            if not self._rtriggered:
                self._rtriggered = True
                self._rtrigger_client.send(b"TRIGGER")
    def trigger_write(self):
        with self._wtrigger_lock:
            if not self._wtriggered:
                self._wtriggered = True
                self._wtrigger_client.send(b"TRIGGER")

    def trigger(self,
            func: typing.Optional[typing.Callable[[], typing.Any]]=None
            ) -> typing.Any:
        func = func or (lambda: None)

        if utils.is_main_thread():
            returned = func()
            self._trigger_both()
            return returned

        func_queue = queue.Queue(1) # type: queue.Queue[str]

        def _action():
            try:
                returned = func()
                type = TriggerResult.Return
            except Exception as e:
                returned = e
                type = TriggerResult.Exception
            func_queue.put([type, returned])
        self._event_queue.put(_action)

        type, returned = func_queue.get(block=True)

        self._trigger_both()

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
        self._read_poll.register(server.fileno(), select.EPOLLIN)
        return True

    def next_send(self) -> typing.Optional[float]:
        next = None
        for server in self.servers.values():
            timeout = server.socket.send_throttle_timeout()
            if (server.socket.waiting_throttled_send() and
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

    def disconnect(self, server: IRCServer.Server):
        try:
            self._read_poll.unregister(server.fileno())
        except FileNotFoundError:
            pass
        try:
            self._write_poll.unregister(server.fileno())
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

    def _daemon_thread(self, target: typing.Callable[[], None]):
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        return thread

    def run(self):
        self._read_thread = self._daemon_thread(self._read_loop)
        self._write_thread = self._daemon_thread(self._write_loop)
        self._event_loop()

    def _event_loop(self):
        while self.running:
            item = self._event_queue.get(block=True, timeout=None)
            item()

    def _write_loop(self):
        while self.running:
            if not self.servers:
                break

            for fd, server in self.servers.items():
                if server.socket.waiting_immediate_send():
                    self._write_poll.register(fd, select.EPOLLOUT)

            events = self._write_poll.poll()
            for fd, event in events:
                if fd == self._wtrigger_server.fileno():
                    # throw away data from trigger socket
                    self._wtrigger_server.recv(1024)
                    with self._wtrigger_lock:
                        self._wtriggered = False
                elif event & select.EPOLLOUT:
                    self._write_poll.unregister(fd)
                    server = self.servers[fd]

                    try:
                        lines = server._send()
                    except:
                        self.log.error("Failed to write to %s", [str(server)])
                        raise
                    self._event_queue.put(lambda: server._post_send(lines))

    def _read_loop(self):
        while self.running:
            if not self.servers:
                self.running = False
                self._event_queue.put(lambda: None)
                break

            self.trigger(self._check)

            events = self._read_poll.poll(self.get_poll_timeout())

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
                if fd == self._rtrigger_server.fileno():
                    # throw away data from trigger socket
                    self._rtrigger_server.recv(1024)
                    with self._rtrigger_lock:
                        self._rtriggered = False
                else:
                    server = self.servers[fd]
                    if event & select.EPOLLIN:
                        lines = server.read()
                        if lines == None:
                            server.disconnect()
                            continue

                        self._event_queue.put(lambda: server._post_read(lines))
                    elif event & select.EPOLLHUP:
                        self.log.warn("Recieved EPOLLHUP for %s", [str(server)])
                        server.disconnect()

    def _check(self):
        self._timers.call()
        self.cache.expire()

        throttle_filled = False
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
            elif (server.socket.waiting_throttled_send() and
                    server.socket.throttle_done()):
                server.socket._fill_throttle()
                throttle_filled = True

        if throttle_filled:
            self._wtrigger_client.send(b"TRIGGER")
