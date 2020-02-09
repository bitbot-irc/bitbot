#--depends-on commands

import re
from src import ModuleManager, utils

REGEX_FACTOID = re.compile("{!([^}]+)}", re.I)

class Module(ModuleManager.BaseModule):
    def _get_factoid(self, targets, factoid):
        setting = "factoid-%s" % factoid
        for target_type, target in targets:
            value = target.get_setting(setting, None)
            if not value == None:
                return target_type, value
        return None
    def _all_factoids(self, targets):
        factoids = {}
        for target in targets:
            for factoid, value in target.find_settings(prefix="factoid-"):
                factoid = factoid.replace("factoid-", "", 1)
                if not factoid in factoids:
                    factoids[factoid] = value
        return factoids

    def _set_factoid(self, target, factoid, value):
        target.set_setting("factoid-%s" % factoid, value)
    def _del_factoid(self, target, factoid):
        target.del_setting("factoid-%s" % factoid)

    def _format_factoid(self, s, targets, depth=0):
        if depth == 5:
            return

        for match in REGEX_FACTOID.finditer(s):
            key = match.group(1)
            value = self._get_factoid(targets, key)
            if value:
                target_desc, value = value
                value = self._format_factoid(value, targets, depth+1)
                s = s.replace(match.group(0), value, 1)
        return s

    @utils.hook("received.command.factoid", permission="factoid")
    @utils.hook("received.command.cfactoid", require_mode="o",
        require_access="low,factoid")
    @utils.kwarg("help", "Set or get a factoid")
    @utils.spec("!'list")
    @utils.spec("!'get !<name>wordlower")
    @utils.spec("!'add !<name>wordlower !<value>string")
    @utils.spec("!'remove !<name>wordlower")
    def factoid(self, event):
        factoid = event["spec"].get(1, None)

        if event["command"] == "cfactoid":
            target = event["target"]
            target_desc = "channel"
        else:
            target = event["server"]
            target_desc = "server"

        exists = False
        if not factoid == None:
            exists = not self._get_factoid([["", target]], factoid) == None

        if event["spec"][0] == "list":
            all_factoids = self._all_factoids(target)
            event["stdout"].write("Available %s factoids: %s"
                % (target_desc, ", ".join(sorted(all_factoids.keys()))))

        elif event["spec"][0] == "get":
            targets = [["server", event["server"]], ["channel", event["target"]]]
            value = self._get_factoid(targets, factoid)
            if value == None:
                raise utils.EventError("Unknown %s factoid '%s'" % factoid)
            target_desc, value = value
            event["stdout"].write("%s: %s" % (factoid, value))

        elif event["spec"][0] == "add":
            if exists:
                raise utils.EventError("%s factoid '%s' already exists"
                    % (target_desc.title(), factoid))
            self._set_factoid(target, factoid, event["spec"][2])
            event["stdout"].write("Set %s factoid '%s'"
                % (target_desc, factoid))

        elif event["spec"][0] == "remove":
            if not exists:
                raise utils.EventError("%s factoid '%s' doesn't exist"
                    % (target_desc.title(), factoid))
            self._del_factoid(target, factoid)
            event["stdout"].write("Removed %s factoid '%s'"
                % (target_desc, factoid))


    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("command", "factoid")
    @utils.kwarg("pattern", REGEX_FACTOID)
    def channel_message(self, event):
        targets = [["server", event["server"]], ["channel", event["target"]]]
        factoid = event["match"].group(1)
        value = self._get_factoid(targets, factoid)
        if not value == None:
            target_desc, value = value
            value = self._format_factoid(value, targets)
            event["stdout"].write("%s: %s" % (factoid, value))
