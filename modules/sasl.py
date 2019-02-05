import base64, hashlib, hmac, uuid
from src import ModuleManager, utils

def _validate(self, s):
    mechanism = s
    if " " in s:
        mechanism, arguments = s.split(" ", 1)
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
                first_base = "n=%s,r=%s" % (
                    _scram_escape(sasl_username), _scram_nonce())
                first_withchannel = "n,,%s" % first_base
                auth_text = first_withchannel.encode("utf8")
                event["server"]._scram_first = first_base.encode("utf8")
                self.log.debug("SCRAM client-first-message: %s",
                    [first_withchannel])
            else:
                data = base64.b64decode(event["message"]).decode("utf8")
                pieces = dict(piece.split("=", 1) for piece in data.split(","))
                if "s" in pieces:
                    # server-first-message
                    self.log.debug("SCRAM server-first-message: %s", [data])

                    nonce = pieces["r"].encode("utf8")
                    salt = base64.b64decode(pieces["s"])
                    iterations = pieces["i"]
                    password = sasl_password.encode("utf8")
                    self.log.debug("SCRAM server-first-message salt: %s",
                        [salt])

                    salted_password = hashlib.pbkdf2_hmac(algo, password, salt,
                        int(iterations), dklen=None)
                    self.log.debug("SCRAM server-first-message salted: %s",
                        [salted_password])
                    event["server"]._scram_salted_password = salted_password

                    client_key = hmac.digest(salted_password, b"Client Key",
                        algo)
                    stored_key = hashlib.new(algo, client_key).digest()

                    channel = base64.b64encode(b"n,,")
                    auth_noproof = b"c=%s,r=%s" % (channel, nonce)
                    auth_message = b"%s,%s,%s" % (event["server"]._scram_first,
                        data.encode("utf8"), auth_noproof)
                    self.log.debug("SCRAM server-first-message auth msg: %s",
                        [auth_message])
                    event["server"]._scram_auth_message = auth_message

                    client_signature = hmac.digest(stored_key, auth_message,
                        algo)
                    client_proof = base64.b64encode(
                        _scram_xor(client_key, client_signature))

                    auth_text = auth_noproof + (b",p=%s" % client_proof)
                elif "v" in pieces:
                    # server-final-message
                    verifier = pieces["v"]

                    salted_password = event["server"]._scram_salted_password
                    auth_message = event["server"]._scram_auth_message
                    server_key = hmac.digest(salted_password, b"Server Key",
                        algo)
                    server_signature = hmac.digest(server_key, auth_message,
                        algo)

                    if server_signature != base64.b64decode(verifier):
                        raise ValueError("SCRAM %s authentication failed "
                            % algo)
                        event["server"].disconnect()
                    auth_text = "+"

        else:
            raise ValueError("unknown sasl mechanism '%s'" % mechanism)

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
        self._end_sasl(event["server"])
