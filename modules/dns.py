import socket
from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    _name = "DNS"

    @Utils.hook("received.command.dns", min_args=1)
    def dns(self, event):
        """
        :help: Get all addresses for a given hostname (IPv4/IPv6)
        :usage: <hostname>
        """
        hostname = event["args_split"][0]
        try:
            address_info = socket.getaddrinfo(hostname, 1, 0,
                socket.SOCK_DGRAM)
        except socket.gaierror:
            event["stderr"].write("Failed to find hostname")
            return
        ips = []
        for _, _, _, _, address in address_info:
            ips.append(address[0])
        event["stdout"].write("%s: %s" % (hostname, ", ".join(ips)))
