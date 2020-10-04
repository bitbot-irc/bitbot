import collections

class DNSBL(object):
    def __init__(self, hostname=None):
        if not hostname == None:
            self.hostname = hostname

    def process(self, a_record, txt_record):
        out = a_record
        if txt_record is not None:
            out += f" - {txt_record}"
        return out

class ZenSpamhaus(DNSBL):
    hostname = "zen.spamhaus.org"
    def process(self, a_record, txt_record):
        result = a_record.rsplit(".", 1)[1]
        if result in ["2", "3", "9"]:
            desc = "spam"
        elif result in ["4", "5", "6", "7"]:
            desc = "exploits"
        else:
            desc = "unknown"
        return f"{result} - {desc}"

class EFNetRBL(DNSBL):
    hostname = "rbl.efnetrbl.org"
    def process(self, a_record, txt_record):
        result = a_record.rsplit(".", 1)[1]
        if result == "1":
            desc = "proxy"
        elif result in ["2", "3"]:
            desc = "spamtap"
        elif result == "4":
            desc = "tor"
        elif result == "5":
            desc = "flooding"
        return f"{result} - {desc}"

class DroneBL(DNSBL):
    hostname = "dnsbl.dronebl.org"

class AbuseAtCBL(DNSBL):
    hostname = "cbl.abuseat.org"
    def process(self, a_record, txt_record):
        result = a_record.rsplit(".", 1)[1]
        if result == "2":
            desc = "abuse"
        else:
            desc = "unknown"
        return f"{result} - {desc}"

class TorExitDan(DNSBL):
    hostname = "torexit.dan.me.uk"
    def process(self, a_record, txt_record):
        return "tor exit"

DEFAULT_LISTS = [
    ZenSpamhaus(),
    EFNetRBL(),
    DroneBL(),
    AbuseAtCBL(),
    TorExitDan()
]

def default_lists():
    return collections.OrderedDict(
        (dnsbl.hostname, dnsbl) for dnsbl in DEFAULT_LISTS)
