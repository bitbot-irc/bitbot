import os, select, sys, threading, time, traceback, uuid
from . import EventManager, Exports, IRCServer, Logging, ModuleManager

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
        self.timers = timers

        events.on("timer.reconnect").hook(self.reconnect)
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.servers = {}
        self.running = True
        self.poll = select.epoll()

    def add_server(self, server_id, connect=True):
        (_, alias, hostname, port, password, ipv4, tls, bindhost, nickname,
            username, realname) = self.database.servers.get(server_id)

        new_server = IRCServer.Server(self, self._events, server_id, alias,
            hostname, port, password, ipv4, tls, bindhost, nickname, username,
            realname)
        if not new_server.get_setting("connect", True):
            return
        self._events.on("new.server").call(server=new_server)
        if connect and new_server.get_setting("connect", True):
            self.connect(new_server)
        return new_server

    def get_server(self, id):
        for server in self.servers.values():
            if server.id == id:
                return server

    def connect(self, server):
        try:
            server.connect()
        except:
            sys.stderr.write("Failed to connect to %s\n" % str(server))
            traceback.print_exc()
            return False
        self.servers[server.fileno()] = server
        self.poll.register(server.fileno(), select.EPOLLOUT)
        return True

    def next_send(self):
        next = None
        for server in self.servers.values():
            timeout = server.send_throttle_timeout()
            if server.waiting_send() and (next == None or timeout < next):
                next = timeout
        return next

    def next_ping(self):
        timeouts = []
        for server in self.servers.values():
            timeout = server.until_next_ping()
            if not timeout == None:
                timeouts.append(timeout)
        if not timeouts:
            return None
        return min(timeouts)
    def next_read_timeout(self):
        timeouts = []
        for server in self.servers.values():
            timeouts.append(server.until_read_timeout())
        if not timeouts:
            return None
        return min(timeouts)

    def get_poll_timeout(self):
        timeouts = []
        timeouts.append(self.timers.next())
        timeouts.append(self.next_send())
        timeouts.append(self.next_ping())
        timeouts.append(self.next_read_timeout())
        timeouts.append(self.cache.next_expiration())
        return min([timeout for timeout in timeouts if not timeout == None])

    def register_read(self, server):
        self.poll.modify(server.fileno(), select.EPOLLIN)
    def register_write(self, server):
        self.poll.modify(server.fileno(), select.EPOLLOUT)
    def register_both(self, server):
        self.poll.modify(server.fileno(),
            select.EPOLLIN|select.EPOLLOUT)

    def disconnect(self, server):
        try:
            self.poll.unregister(server.fileno())
        except FileNotFoundError:
            pass
        del self.servers[server.fileno()]

    def reconnect(self, event):
        server = self.add_server(event["server_id"], False)
        if self.connect(server):
            self.servers[server.fileno()] = server
        else:
            event["timer"].redo()

    def set_setting(self, setting, value):
        self.database.bot_settings.set(setting, value)
    def get_setting(self, setting, default=None):
        return self.database.bot_settings.get(setting, default)
    def find_settings(self, pattern, default=[]):
        return self.database.bot_settings.find(pattern, default)
    def find_settings_prefix(self, prefix, default=[]):
        return self.database.bot_settings.find_prefix(
            prefix, default)
    def del_setting(self, setting):
        self.database.bot_settings.delete(setting)

    def run(self):
        while self.running:
            events = self.poll.poll(self.get_poll_timeout())
            self.lock.acquire()
            self.timers.call()
            self.cache.expire()

            for fd, event in events:
                if fd in self.servers:
                    server = self.servers[fd]
                    if event & select.EPOLLIN:
                        lines = server.read()
                        for line in lines:
                            self.log.debug("%s (raw) | %s", [str(server), line])
                            server.parse_line(line)
                    elif event & select.EPOLLOUT:
                        server._send()
                        self.register_read(server)
                    elif event & select.EPULLHUP:
                        print("hangup")
                        server.disconnect()

            for server in list(self.servers.values()):
                if server.read_timed_out():
                    print("pingout from %s" % str(server))
                    server.disconnect()
                elif server.ping_due() and not server.ping_sent:
                    server.send_ping()
                    server.ping_sent = True
                if not server.connected:
                    self.disconnect(server)

                    reconnect_delay = self.config.get("reconnect-delay", 10)
                    self.timers.add("reconnect", reconnect_delay,
                        server_id=server.id)

                    print("disconnected from %s, reconnecting in %d seconds" % (
                        str(server), reconnect_delay))
                elif server.waiting_send() and server.throttle_done():
                    self.register_both(server)
            self.lock.release()
