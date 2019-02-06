import base64, hashlib, hmac, uuid
from src import ModuleManager, utils
from . import scram

def _validate(self, s):
    mechanism, _, arguments = s.partition(" ")
    return {"mechanism": mechanism, "args": arguments}

def _scram_nonce():
    return str(uuid.uuid4().hex)
def _scram_escape(s):
    return s.replace("=", "=3D").replace(",", "=2C")
def _scram_unescape(s):
    return s.replace("=3D", "=").replace("=2C", ",")
def _scram_xor(s1, s2):
    return bytes(a ^ b for a, b in zip(s1, s2))

@utils.export("serverset", {"setting": "sasl",
    "help": "Set the sasl username/password for this server",
    "validate": _validate})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.cap.ls")
    def on_cap(self, event):
        has_sasl = "sasl" in event["capabilities"]
        our_sasl = event["server"].get_setting("sasl", None)

        do_sasl = False
        if has_sasl and our_sasl:
            if not event["capabilities"]["sasl"] == None:
                our_mechanism = our_sasl["mechanism"].upper()
                do_sasl = our_mechanism in event["capabilities"
                    ]["sasl"].split(",")
            else:
                do_sasl = True

        if do_sasl:
            event["server"].queue_capability("sasl")

    @utils.hook("received.cap.ack")
    def on_cap_ack(self, event):
        if "sasl" in event["capabilities"]:
            sasl = event["server"].get_setting("sasl")
            event["server"].send_authenticate(sasl["mechanism"].upper())
            event["server"].wait_for_capability("sasl")

    @utils.hook("received.authenticate")
    def on_authenticate(self, event):
        sasl = event["server"].get_setting("sasl")
        mechanism = sasl["mechanism"].upper()

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
            algo = mechanism.split("SCRAM-", 1)[1].replace("-", "")
            sasl_username, sasl_password = sasl["args"].split(":", 1)
            if event["message"] == "+":
                # start SCRAM handshake
                event["server"]._scram = scram.SCRAM(
                    algo, sasl_username, sasl_password)
                auth_text = event["server"]._scram.client_first()
            else:
                current_scram = event["server"]._scram
                data = base64.b64decode(event["message"])
                if current_scram.state == scram.SCRAMState.ClientFirst:
                    auth_text = current_scram.server_first(data)
                elif current_scram.state == scram.SCRAMState.ClientFinal:
                    verified = current_scram.server_final(data)
                    del event["server"]._scram

                    if verified:
                        auth_text = "+"
                    else:
                        if current_scram.state == scram.SCRAMState.VerifyFailed:
                            event["server"].disconnect()
                            raise ValueError("Server SCRAM verification failed")

        else:
            raise ValueError("unknown sasl mechanism '%s'" % mechanism)

        if not auth_text == None:
            if not auth_text == "+":
                auth_text = base64.b64encode(auth_text)
                auth_text = auth_text.decode("utf8")
            event["server"].send_authenticate(auth_text)

    def _end_sasl(self, server):
        server.capability_done("sasl")

    @utils.hook("received.numeric.903")
    def sasl_success(self, event):
        self._end_sasl(event["server"])
    @utils.hook("received.numeric.904")
    def sasl_failure(self, event):
        self.log.warn("SASL failure: %s", [event["args"][1]])
        self._end_sasl(event["server"])
