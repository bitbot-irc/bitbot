import ipaddress
from src import ModuleManager, utils
import dns.resolver
from . import lists as _lists

class Module(ModuleManager.BaseModule):
    _name = "DNSBL"

    @utils.hook("received.command.dnsbl")
    def dnsbl(self, event):
        args = event["args_split"]

        default_lists = _lists.default_lists()
        lists = []
        for i, arg in reversed(list(enumerate(args))):
            if arg[0] == "@":
                hostname = args.pop(i)[1:]
                if hostname in default_lists:
                    lists.insert(0, default_lists[hostname])
                else:
                    lists.insert(0, _lists.DNSBL(hostname))

        lists = lists or list(default_lists.values())

        address = args[0]
        failed = self._check_lists(lists, address)
        if failed:
            failed = ["%s (%s)" % item for item in failed]
            event["stderr"].write("%s matched for lists: %s" %
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
            record = self._check_list(list.hostname, address)
            if record is not None:
                a_record, txt_record = record
                reason = list.process(a_record, txt_record) or "unknown"
                failed.append((list.hostname, reason))
        return failed

    def _check_list(self, list, address):
        list_address = "%s.%s" % (address, list)
        try:
            a_record = dns.resolver.resolve(list_address, "A")[0].to_text()
        except dns.resolver.NXDOMAIN:
            return None

        try:
            txt_record = dns.resolver.resolve(list_address, "TXT")[0].to_text()
        except:
            txt_record = None

        return (a_record, txt_record)
