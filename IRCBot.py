import os, select, sys, threading, time, traceback
import EventManager, IRCServer, ModuleManager, Timer

class Bot(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.database = None
        self.config = None
        self.bot_directory = os.path.dirname(os.path.realpath(__file__))
        self.servers = {}
        self.running = True
        self.poll = select.epoll()
        self.modules = ModuleManager.ModuleManager(self)
        self.events = EventManager.EventHook(self)
        self.timers = []

    def add_server(self, id, hostname, port, password, ipv4, tls,
            nickname, username, realname, connect=False):
        new_server = IRCServer.Server(id, hostname, port, password,
             ipv4, tls, nickname, username, realname, self)
        self.events.on("new").on("server").call(server=new_server)
        self.servers[new_server.fileno()] = new_server
        if connect:
            self.connect(new_server)
    def connect(self, server):
        try:
            server.connect()
        except:
            sys.stderr.write("Failed to connect to %s\n" % str(server))
            traceback.print_exc()
            return False
        self.poll.register(server.fileno(), select.EPOLLOUT)
        return True
    def connect_all(self):
        for server in self.servers.values():
            self.connect(server)

    def add_timer(self, function, delay, *args, **kwargs):
        timer = Timer.Timer(function, delay, *args, **kwargs)
        timer.set_started_time()
        self.timers.append(timer)
    def next_timer(self):
        next = None
        for timer in self.timers:
            time_left = timer.time_left()
            if not next or time_left < next:
                next = time_left
        return next or 30
    def call_timers(self):
        for timer in self.timers[:]:
            if timer.due():
                timer.call()
                if timer.done():
                    self.timers.remove(timer)

    def register_read(self, server):
        self.poll.modify(server.fileno(), select.EPOLLIN)
    def register_write(self, server):
        self.poll.modify(server.fileno(), select.EPOLLOUT)
    def register_both(self, server):
        self.poll.modify(server.fileno(),
            select.EPOLLIN|select.EPOLLOUT)

    def since_last_read(self, server):
        return None if not server.last_read else time.time(
            )-server.last_read

    def disconnect(self, server):
        self.poll.unregister(server.fileno())
        del self.servers[server.fileno()]

    def reconnect(self, timer, server):
        IRCServer.Server.__init__(server, server.id, server.hostname,
            server.port, server.password, server.ipv4, server.tls,
            server.nickname, server.username, server.realname, self)
        if self.connect(server):
            self.servers[server.fileno()] = server
        else:
            timer.redo()
    def run(self):
        while self.running:
            self.lock.acquire()
            events = self.poll.poll(self.next_timer())
            self.call_timers()
            for fd, event in events:
                if fd in self.servers:
                    server = self.servers[fd]
                    if event & select.EPOLLIN:
                        lines = server.read()
                        for line in lines:
                            print(line)
                            server.parse_line(line)
                    elif event & select.EPOLLOUT:
                        server._send()
                        self.register_read(server)
                    elif event & select.EPULLHUP:
                        print("hangup")
                        server.disconnect()

            for server in list(self.servers.values()):
                since_last_read = self.since_last_read(server)
                if since_last_read:
                    if since_last_read > 120:
                        print("pingout from %s" % str(server))
                        server.disconnect()
                    elif since_last_read > 30 and not server.ping_sent:
                        server.send_ping()
                        server.ping_sent = True
                if not server.connected:
                    self.disconnect(server)

                    reconnect_delay = self.config.get("reconnect-delay", 10)
                    self.add_timer(self.reconnect, reconnect_delay, server)

                    print("disconnected from %s, reconnecting in %d seconds" % (
                        str(server), reconnect_delay))
                elif server.waiting_send():
                    self.register_both(server)
            self.lock.release()
