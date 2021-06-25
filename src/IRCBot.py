VERSION: str = ""
with open("VERSION", "r") as version_file:
    VERSION = "v%s" % version_file.read().strip()
SOURCE: str = "https://git.io/bitbot"
URL: str = "https://bitbot.dev"

import enum, queue, os, queue, select, socket, sys, threading, time, traceback
import typing, uuid
from src import Config, EventManager, Exports, IRCServer, Logging
from src import ModuleManager, PollHook, PollSource, Socket, Timers, utils

class TriggerResult(enum.Enum):
    Return = 1
    Exception = 2

class TriggerEventType(enum.Enum):
    Action = 1
    Kill = 2
class TriggerEvent(object):
    def __init__(self, type: TriggerEventType,
            callback: typing.Callable[[], None]=None):
        self.type = type
        self.callback = callback

class ListLambdaPollHook(PollHook.PollHook):
    def __init__(self,
            collection: typing.Callable[[], typing.Iterable[typing.Any]],
            func: typing.Callable[[typing.Any], None]):
        self._collection = collection
        self._func = func
    def next(self):
        timeouts = [self._func(i) for i in self._collection()]
        timeouts = [t for t in timeouts if t is not None]
        return min(timeouts or [None])

class Bot(object):
    def __init__(self, directory, data_directory, args, cache, config, database,
            events, exports, log, modules, timers):
        self.directory = directory
        self.data_directory = data_directory
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
        self._writing = False
        self._reading = False
        self.servers = {}
        self.reconnections = {}

        self._event_queue = queue.Queue() # type: typing.Queue[TriggerEvent]

        self._read_poll = select.poll()
        self._write_poll = select.poll()

        self._rtrigger_server, self._rtrigger_client = socket.socketpair()
        self._read_poll.register(self._rtrigger_server.fileno(), select.POLLIN)

        self._rtrigger_lock = threading.Lock()
        self._rtriggered = False
        self._write_condition = threading.Condition()

        self._read_thread = None
        self._write_thread = None

        self._poll_timeouts = [] # typing.List[PollHook.PollHook]
        self._poll_timeouts.append(ListLambdaPollHook(
            lambda: self.servers.values(),
            lambda server: server.until_read_timeout()))

        self._poll_timeouts.append(ListLambdaPollHook(
            lambda: self.servers.values(),
            lambda server: server.until_next_ping()))

        self._poll_timeouts.append(ListLambdaPollHook(
            lambda: self.servers.values(), self._throttle_timeout))

        self._poll_sources = [] # typing.List[PollSource.PollSource]

    def add_poll_hook(self, hook: PollHook.PollHook):
        self._poll_timeouts.append(hook)
    def add_poll_source(self, source: PollSource.PollSource):
        self._poll_sources.append(source)

    def _throttle_timeout(self, server: IRCServer.Server):
        if server.socket.waiting_throttled_send():
            return server.socket.send_throttle_timeout()
        return None

    def _trigger_both(self):
        self.trigger_read()
        self.trigger_write()
    def trigger_read(self):
        with self._rtrigger_lock:
            if not self._rtriggered:
                self._rtriggered = True
                self._rtrigger_client.send(b"TRIGGER")
    def trigger_write(self):
        with self._write_condition:
            self._write_condition.notify()

    def trigger(self,
            func: typing.Optional[typing.Callable[[], typing.Any]]=None,
            trigger_threads=True) -> typing.Any:
        func = func or (lambda: None)

        if utils.is_main_thread():
            returned = func()
            if trigger_threads:
                self._trigger_both()
            return returned

        func_queue: queue.Queue[typing.Tuple[TriggerResult, typing.Any]
            ] = queue.Queue(1)

        def _action():
            try:
                returned = func()
                type = TriggerResult.Return
            except Exception as e:
                returned = e
                type = TriggerResult.Exception
            func_queue.put([type, returned])
        event_item = TriggerEvent(TriggerEventType.Action, _action)
        self._event_queue.put(event_item)

        type, returned = func_queue.get(block=True)

        if trigger_threads:
            self._trigger_both()

        if (type == TriggerResult.Exception and
                isinstance(returned, Exception)):
            raise returned
        elif type == TriggerResult.Return:
            return returned

    def panic(self, reason):
        exc_info = False
        if any(sys.exc_info()):
            exc_info = True

        self.log.critical("panic() called: %s", [reason], exc_info=exc_info)
        sys.exit(utils.consts.Exit.PANIC)

    def get_config(self, name: str) -> Config.Config:
        path = os.path.join(self.data_directory, "%s.conf" % name)
        config = Config.Config(name, path)
        config.load()
        return config

    def _module_lists(self):
        module_lists = self.get_config("modules")
        whitelist = module_lists.get_list("whitelist")
        blacklist = module_lists.get_list("blacklist")

        return whitelist, blacklist

    def load_modules(self
            ) -> typing.Tuple[typing.List[str], typing.List[str]]:
        whitelist, blacklist = self._module_lists()
        return self.modules.load_modules(self, whitelist=whitelist,
            blacklist=blacklist)
    def try_reload_modules(self) -> ModuleManager.TryReloadResult:
        whitelist, blacklist = self._module_lists()
        return self.modules.try_reload_modules(self, whitelist=whitelist,
            blacklist=blacklist)

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
            ip = ""
            if server.socket.connected_ip is not None:
                ip = f" ({server.socket.connected_ip})"

            self.log.warn("Failed to connect to %s%s: %s",
                [str(server), ip, str(e)])
            self.log.debug("Connection failure reason:", exc_info=True)
            return False
        self.servers[server.fileno()] = server
        self._read_poll.register(server.fileno(), select.POLLIN)
        return True

    def get_poll_timeout(self) -> float:
        timeouts = []
        for poll_timeout in self._poll_timeouts:
            timeouts.append(poll_timeout.next())

        min_secs = min([timeout for timeout in timeouts if not timeout == None])
        return max([min_secs, 0])

    def disconnect(self, server: IRCServer.Server):
        del self.servers[server.fileno()]
        self._trigger_both()

    def _timed_reconnect(self, timer: Timers.Timer):
        server_id = timer.kwargs["server_id"]
        params = timer.kwargs.get("connection_params", None)
        if not self.reconnect(server_id, params):
            timer.redo()
        else:
            del self.reconnections[server_id]
    def reconnect(self, server_id: int, connection_params: typing.Optional[
            utils.irc.IRCConnectionParameters]=None) -> bool:
        args = {} # type: typing.Dict[str, str]
        if not connection_params == None:
            args = typing.cast(utils.irc.IRCConnectionParameters,
                connection_params).args

        server = self.add_server(server_id, False, args)
        server.reconnected = True
        if self.connect(server):
            self.servers[server.fileno()] = server
            return True
        return False

    def set_setting(self, setting: str, value: typing.Any):
        self.database.bot_settings.set(setting, value)
    def get_setting(self, setting: str, default: typing.Any=None) -> typing.Any:
        return self.database.bot_settings.get(setting, default)
    def find_settings(self, pattern: str=None, prefix: str=None,
            default: typing.Any=[]) -> typing.List[typing.Any]:
        if not pattern == None:
            return self.database.bot_settings.find(pattern, default)
        elif not prefix == None:
            return self.database.bot_settings.find_prefix(prefix, default)
        else:
            raise ValueError("Please provide 'pattern' or 'prefix'")

    def del_setting(self, setting: str):
        self.database.bot_settings.delete(setting)

    def _daemon_thread(self, target: typing.Callable[[], None]):
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        return thread

    def run(self):
        self._writing = True
        self._reading = True

        self._read_thread = self._daemon_thread(
            lambda: self._loop_catch("read", self._read_loop))
        self._write_thread = self._daemon_thread(
            lambda: self._loop_catch("write", self._write_loop))
        self._event_loop()

    def stop(self, reason: str="Stopping"):
        self._reading = False # disable read thread
        self.trigger_read()
        for server in self.servers.values():
            line = server.send_quit(reason)
            line.events.on("send").hook(self._shutdown_hook(server))
    def _shutdown_hook(self, server):
        def shutdown(e):
            server.disconnect()
            self.disconnect(server)
            if not self.servers:
                self._writing = False
        return shutdown

    def _kill(self):
        self._writing = False
        self._reading = False
        self._trigger_both()

    def _event_loop(self):
        while ((self._writing or self._reading) or
                not self._event_queue.empty()):
            try:
                item = self._event_queue.get(block=True,
                    timeout=self.get_poll_timeout())
            except queue.Empty:
                # caused by timeout being hit.
                continue
            finally:
                self._check()

            if item.type == TriggerEventType.Action:
                try:
                    item.callback()
                except:
                    self._kill()
                    raise
            elif item.type == TriggerEventType.Kill:
                self._kill()
                if not item.callback == None:
                    item.callback()
                break

    def _post_send_factory(self, server, lines):
        return lambda: server._post_send(lines)
    def _post_read_factory(self, server, lines):
        return lambda: server._post_read(lines)

    def _loop_catch(self, name: str, loop: typing.Callable[[], None]):
        try:
            loop()
        except Exception as e:
            self.panic("Exception on '%s' thread" % name)

    def _write_loop(self):
        while self._writing:
            poll_sources = {}
            with self._write_condition:
                fds = []
                for fd, server in self.servers.items():
                    if server.socket.waiting_immediate_send():
                        fds.append(fd)

                for poll_source in self._poll_sources:
                    for fileno in poll_source.get_writables():
                        poll_sources[fileno] = poll_source
                        fds.append(fileno)

                if not fds:
                    self._write_condition.wait()
                    continue
                else:
                    for fd in fds:
                        self._write_poll.register(fd, select.POLLOUT)

            events = self._write_poll.poll()

            for fd, event in events:
                if event & select.POLLOUT:
                    self._write_poll.unregister(fd)
                    if fd in self.servers:
                        server = self.servers[fd]

                        try:
                            lines = server._send()
                        except:
                            self.log.error("Failed to write to %s",
                                [str(server)])
                            raise
                        event_item = TriggerEvent(TriggerEventType.Action,
                            self._post_send_factory(server, lines))
                        self._event_queue.put(event_item)
                    elif fd in poll_sources:
                        def _trigger(source, fd):
                            return lambda: source.is_writeable(fd)
                        self.trigger(_trigger(poll_sources[fd], fd))

    def _read_loop(self):
        poll_sources = {}
        while self._reading:
            new_poll_sources = {}
            for poll_source in self._poll_sources:
                for fileno in poll_source.get_readables():
                    new_poll_sources[fileno] = poll_source
            for fileno in new_poll_sources:
                if not fileno in poll_sources:
                    poll_sources[fileno] = new_poll_sources[fileno]
                    self._read_poll.register(fileno, select.POLLIN)
            for fileno in list(poll_sources.keys()):
                if not fileno in new_poll_sources:
                    del poll_sources[fileno]
                    self._read_poll.unregister(fileno)

            events = self._read_poll.poll()

            for fd, event in events:
                if fd == self._rtrigger_server.fileno():
                    # throw away data from trigger socket
                    with self._rtrigger_lock:
                        self._rtrigger_server.recv(1024)
                        self._rtriggered = False
                elif fd in poll_sources:
                    def _trigger(source, fd):
                        return lambda: source.is_readable(fd)
                    self.trigger(_trigger(poll_sources[fd], fd))
                else:
                    if not fd in self.servers:
                        self._read_poll.unregister(fd)
                        continue

                    server = self.servers[fd]
                    if event & select.POLLIN:
                        lines = server.read()
                        if lines == None:
                            server.disconnect()
                            continue

                        event_item = TriggerEvent(TriggerEventType.Action,
                            self._post_read_factory(server, lines))
                        self._event_queue.put(event_item)
                    elif event & select.POLLHUP:
                        self.log.warn("Recieved POLLHUP for %s", [str(server)])
                        server.disconnect()

    def _check(self):
        for poll_timeout in self._poll_timeouts:
            if poll_timeout.next() == 0:
                poll_timeout.call()

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

                    timer = self._timers.add("timed-reconnect",
                        self._timed_reconnect, reconnect_delay,
                        server_id=server.id)
                    self.reconnections[server.id] = timer

                    self.log.warn(
                        "Disconnected from %s, reconnecting in %d seconds",
                        [str(server), reconnect_delay])
            elif (server.socket.waiting_throttled_send() and
                    server.socket.throttle_done()):
                server.socket._fill_throttle()
                throttle_filled = True

        if throttle_filled:
            self.trigger_write()
