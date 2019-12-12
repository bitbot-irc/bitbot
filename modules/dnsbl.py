import ipaddress
from src import ModuleManager, utils
import dns.resolver

DEFAULT_LISTS = [
    "rbl.efnetrbl.org",
    "zen.spamhaus.org"
]

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.dnsbl")
    def dnsbl(self, event):
        args = event["args_split"]

        lists = []
        for i, arg in reversed(list(enumerate(args))):
            if arg[0] == "@":
                lists.insert(args.pop(i))
        lists = lists or DEFAULT_LISTS

        address = args[0]
        failed = self._check_lists(lists, address)
        if failed:
            event["stderr"].write("%s failed for lists: %s" %
                (address, ", ".join(failed)))
        else:
            event["stdout"].write("%s not found in blacklists" % address)

    def _check_lists(self, lists, address):
        address_obj = ipaddress.ip_address(address)

        if address_obj.version == 6:
            address = reversed(address_obj.exploded.replace(":", ""))
        else:
            address = reversed(address.split("."))
        address = ".".join(address)

        failed = []
        for list in lists:
            if not self._check_list(list, address):
                failed.append(list)
        return failed

    def _check_list(self, list, address):
        list_address = "%s.%s" % (address, list)
        try:
            dns.resolver.query(list_address)
        except dns.resolver.NXDOMAIN:
            return True
        return False
