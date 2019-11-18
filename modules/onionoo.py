#--depends-on commands
#--depends-on config

import re
from src import EventManager, ModuleManager, utils

REGEX_SHA1_HEX = re.compile("[A-Fa-f0-9]{40}")
URL_ONIONOO_DETAILS = "https://onionoo.torproject.org/details"
URL_RELAY_SEARCH_SEARCH = "https://metrics.torproject.org/rs.html#search/"
URL_RELAY_SEARCH_DETAILS = "https://metrics.torproject.org/rs.html#details/"

def _get_relays_details(search):
    page = utils.http.request(
        URL_ONIONOO_DETAILS, get_params={"search": search}, json=True)
    if page and "relays" in page.data:
        return page.data["relays"]
    raise utils.EventResultsError()

def _format_relay_summary_message(relays, search):
    if len(relays) > 1:
        raise utils.EventError(f"There were {len(relays)} relays found for "
                               f"this query. {URL_RELAY_SEARCH_SEARCH}{search}")
    if not relays:
        raise utils.EventError("There were no relays found for this query.")
    details = relays[0]
    nickname = details["nickname"]
    consensus_weight = details["consensus_weight"]
    flags = " ".join(details["flags"])
    url = URL_RELAY_SEARCH_DETAILS + details["fingerprint"]
    return f"{nickname} - CW: {consensus_weight} [{flags}] {url}"

@utils.export("channelset", utils.BoolSetting("auto-torrelay",
    "Disable/Enable automatically getting Tor relay info from fingerprints"))
class Module(ModuleManager.BaseModule):
    _name = "Onionoo"

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("priority", EventManager.PRIORITY_MONITOR)
    @utils.kwarg("command", "torrelay")
    @utils.kwarg("pattern", REGEX_SHA1_HEX)
    def channel_message(self, event):
        if event["target"].get_setting("auto-torrelay", False):
            event.eat()
            search = event["match"].group(0)
            try:
                relays = _get_relays_details(search)
                event["stdout"].write(
                    _format_relay_summary_message(relays, search))
            except utils.EventError:
                pass

    @utils.hook("received.command.torrelay", min_args=1)
    def torrelay(self, event):
        """
        :help: Get summary information about a Tor relay
        :usage: <fingerprint|nickname>
        """
        search = event["args"]
        relays = _get_relays_details(search)
        event["stdout"].write(_format_relay_summary_message(relays, search))
