#--depends-on config

import base64, hashlib, hmac, uuid
from src import ModuleManager, utils
from . import scram

CAP = utils.irc.Capability("sasl")

USERPASS_MECHANISMS = [
    "SCRAM-SHA-512",
    "SCRAM-SHA-256",
    "SCRAM-SHA-1",
    "PLAIN"
]

def _validate(s):
    mechanism, _, arguments = s.partition(" ")
    return {"mechanism": mechanism, "args": arguments}

@utils.export("serverset", {"setting": "sasl",
    "help": "Set the sasl username/password for this server",
    "validate": _validate, "example": "PLAIN BitBot:hunter2"})
@utils.export("serverset", {"setting": "sasl-hard-fail",
    "help": "Set whether a SASL failure should cause a disconnect",
    "validate": utils.bool_or_none, "example": "on"})
class Module(ModuleManager.BaseModule):
    def _best_userpass_mechanism(self, mechanisms):
        for potential_mechanism in USERPASS_MECHANISMS:
            if potential_mechanism in mechanisms:
                return potential_mechanism

    @utils.hook("received.cap.new")
    @utils.hook("received.cap.ls")
    def on_cap(self, event):
        has_sasl = "sasl" in event["capabilities"]
        our_sasl = event["server"].get_setting("sasl", None)

        do_sasl = False
        if has_sasl and our_sasl:
            if not event["capabilities"]["sasl"] == None:
                our_mechanism = our_sasl["mechanism"].upper()
                server_mechanisms = event["capabilities"]["sasl"].split(",")
                if our_mechanism == "USERPASS":
                    our_mechanism = self._best_userpass_mechanism(
                        server_mechanisms)
                do_sasl = our_mechanism in server_mechanisms
            else:
                do_sasl = True

        if do_sasl:
            cap = CAP.copy()
            cap.on_ack(lambda: self._sasl_ack(event["server"]))
            return cap

    def _sasl_ack(self, server):
        sasl = server.get_setting("sasl")
        mechanism = sasl["mechanism"].upper()
        if mechanism == "USERPASS":
            server_mechanisms = server.server_capabilities["sasl"]
            server_mechanisms = server_mechanisms or [
                USERPASS_MECHANISMS[0]]
            mechanism = self._best_userpass_mechanism(server_mechanisms)

        server.send_authenticate(mechanism)
        server.sasl_mechanism = mechanism
        server.wait_for_capability("sasl")

    @utils.hook("received.authenticate")
    def on_authenticate(self, event):
        sasl = event["server"].get_setting("sasl")
        mechanism = event["server"].sasl_mechanism

        auth_text = None
        if mechanism == "PLAIN":
            if event["message"] != "+":
                event["server"].send_authenticate("*")
            else:
                sasl_username, sasl_password = sasl["args"].split(":", 1)
                auth_text = ("%s\0%s\0%s" % (
                    sasl_username, sasl_username, sasl_password)).encode("utf8")

        elif mechanism == "EXTERNAL":
            if event["message"] != "+":
                event["server"].send_authenticate("*")
            else:
                auth_text = "+"

        elif mechanism.startswith("SCRAM-"):

            if event["message"] == "+":
                # start SCRAM handshake

                # create SCRAM helper
                sasl_username, sasl_password = sasl["args"].split(":", 1)
                algo = mechanism.split("SCRAM-", 1)[1]
                event["server"]._scram = scram.SCRAM(
                    algo, sasl_username, sasl_password)

                # generate client-first-message
                auth_text = event["server"]._scram.client_first()
            else:
                current_scram = event["server"]._scram
                data = base64.b64decode(event["message"])
                if current_scram.state == scram.SCRAMState.ClientFirst:
                    # use server-first-message to generate client-final-message
                    auth_text = current_scram.server_first(data)
                elif current_scram.state == scram.SCRAMState.ClientFinal:
                    # use server-final-message to check server proof
                    verified = current_scram.server_final(data)
                    del event["server"]._scram

                    if verified:
                        auth_text = "+"
                    else:
                        if current_scram.state == scram.SCRAMState.VerifyFailed:
                            # server gave a bad verification so we should panic
                            self._panic(event["server"], "SCRAM VerifyFailed")

        else:
            raise ValueError("unknown sasl mechanism '%s'" % mechanism)

        if not auth_text == None:
            if not auth_text == "+":
                auth_text = base64.b64encode(auth_text)
                auth_text = auth_text.decode("utf8")
            event["server"].send_authenticate(auth_text)

    def _end_sasl(self, server):
        server.capability_done("sasl")

    @utils.hook("received.908")
    def sasl_mechanisms(self, event):
        server_mechanisms = event["line"].args[1].split(",")
        mechanism = self._best_userpass_mechanism(server_mechanimsms)
        event["server"].sasl_mechanism = mechanism
        event["server"].send_authenticate(mechanism)

    @utils.hook("received.903")
    def sasl_success(self, event):
        self._end_sasl(event["server"])
    @utils.hook("received.904")
    def sasl_failure(self, event):
        self._panic(event["server"], "ERR_SASLFAIL (%s)" %
            event["line"].args[1])

    @utils.hook("received.907")
    def sasl_already(self, event):
        self._end_sasl(event["server"])

    def _panic(self, server, message):
        if server.get_setting("sasl-hard-fail", True):
            message = "SASL panic for %s: %s" % (str(server), message)
            if not server.from_init:
                self.log.error(message)
                self.bot.disconnect(server)
            else:
                self.bot.panic(reason=message)
        else:
            self.log.warn("SASL failure for %s: %s" % (str(server), message))
            self._end_sasl(server)
