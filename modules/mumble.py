import datetime, socket, struct
from src import ModuleManager, utils

DEFAULT_PORT = 64738

def _parse(s):
    host, _, port = s.partition(":")
    if port:
        if not port.isdigit():
            return None
    else:
        port = str(DEFAULT_PORT)
    return "%s:%s" % (host, port)

SETTING = utils.FunctionSetting(_parse, "mumble-server",
    "Set the mumble server for this channel",
    example="example.com:%s" % DEFAULT_PORT)

@utils.export("channelset", SETTING)
@utils.export("serverset", SETTING)
class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.mumble")
    @utils.kwarg("help", "Get user and bandwidth stats for a mumble server")
    @utils.kwarg("usage", "[server[:<port>]]")
    def mumble(self, event):
        server = None
        if not event["args"]:
            server = event["target"].get_setting("mumble-server",
                event["server"].get_setting("mumble-server", None))
        elif event["args"]:
            server = event["args_split"][0]
        if not server:
            raise utils.EventError("Please provide a server")

        server, _, port = server.partition(":")
        if port:
            if not port.isdigit():
                raise utils.EventError("Port must be numeric")
            port = int(port)
        else:
            port = DEFAULT_PORT

        timestamp = datetime.datetime.utcnow().microsecond
        ping_packet = struct.pack(">iQ", 0, timestamp)
        s = socket.socket(type=socket.SOCK_DGRAM)
        s.settimeout(5)

        with utils.deadline():
            try:
                s.sendto(ping_packet, (server, port))
            except socket.gaierror as e:
                raise utils.EventError(str(e))

            try:
                pong_packet = s.recv(24)
            except socket.timeout:
                raise utils.EventError(
                    "Timed out waiting for response from %s:%d"
                    % (server, port))

        pong = struct.unpack(">bbbbQiii", pong_packet)

        version = ".".join(str(v) for v in pong[1:4])
        ping = (datetime.datetime.utcnow().microsecond-timestamp)/1000
        users = pong[5]
        max_users = pong[6]
        bandwidth = pong[7]/1000 # kbit/s

        event["stdout"].write(
            "%s:%d (v%s): %d/%d users, %.1fms ping, %dkbit/s bandwidth"
            % (server, port, version, users, max_users, ping, bandwidth))
