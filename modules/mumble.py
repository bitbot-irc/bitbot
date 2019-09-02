import datetime, socket, struct
from src import ModuleManager, utils

DEFAULT_PORT = 64738

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.mumble")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Get user and bandwidth stats for a mumble server")
    @utils.kwarg("usage", "<server>[:<port>]")
    def mumble(self, event):
        server, _, port = event["args_split"][0].partition(":")
        if port:
            if not port.isdigit():
                raise utils.EventError("Port must be numeric")
            port = int(port)
        else:
            port = DEFAULT_PORT

        timestamp = datetime.datetime.utcnow().microsecond
        ping_packet = struct.pack(">iQ", 0, timestamp)
        s = socket.socket(type=socket.SOCK_DGRAM)
        s.sendto(ping_packet, (server, port))

        pong_packet = s.recv(24)
        pong = struct.unpack(">bbbbQiii", pong_packet)

        version = ".".join(str(v) for v in pong[1:4])
        ping = (datetime.datetime.utcnow().microsecond-timestamp)/1000
        users = pong[5]
        max_users = pong[6]
        bandwidth = pong[7]/1000 # kbit/s

        event["stdout"].write(
            "%s (v%s): %d/%d users, %.1fms ping, %dkbit/s bandwidth"
            % (server, version, users, max_users, ping, bandwidth))
