import base64, enum, hashlib, hmac, typing, uuid

def _scram_nonce():
    return uuid.uuid4().hex.encode("utf8")
def _scram_escape(s):
    return s.replace(b"=", b"=3D").replace(b",", b"=2C")
def _scram_unescape(s):
    return s.replace(b"=3D", b"=").replace(b"=2C", b",")
def _scram_xor(s1, s2):
    return bytes(a ^ b for a, b in zip(s1, s2))

class SCRAMState(enum.Enum):
    Uninitialised = 0
    ClientFirst = 1
    ClientFinal = 2
    Success = 3
    VerifyFailed = 4

class SCRAMError(Exception):
    pass

class SCRAM(object):
    def __init__(self, algo, username, password):
        self._algo = algo
        self._username = username.encode("utf8")
        self._password = password.encode("utf8")

        self.state = SCRAMState.Uninitialised
        self._client_first = None
        self._salted_password = None
        self._auth_message = None

    def _get_pieces(self, data: bytes) -> typing.Dict[bytes, bytes]:
        return dict(piece.split(b"=", 1) for piece in data.split(b","))

    def _hmac(self, key: bytes, msg: bytes) -> bytes:
        return hmac.digest(key, msg, self._algo)
    def _hash(self, msg: bytes) -> bytes:
        return hashlib.new(self._algo, msg).digest()

    def client_first(self) -> bytes:
        self.state = SCRAMState.ClientFirst
        # start SCRAM handshake
        self._client_first = b"n=%s,r=%s" % (
            _scram_escape(self._username), _scram_nonce())
        return b"n,,%s" % self._client_first

    def server_first(self, data: bytes) -> bytes:
        self.state = SCRAMState.ClientFinal

        pieces = self._get_pieces(data)
        # server-first-message
        nonce = pieces[b"r"]
        salt = base64.b64decode(pieces[b"s"])
        iterations = pieces[b"i"]
        password = self._password

        salted_password = hashlib.pbkdf2_hmac(self._algo, password, salt,
            int(iterations), dklen=None)
        self._salted_password = salted_password

        client_key = self._hmac(salted_password, b"Client Key")
        stored_key = self._hash(client_key)

        channel = base64.b64encode(b"n,,")
        auth_noproof = b"c=%s,r=%s" % (channel, nonce)
        auth_message = b"%s,%s,%s" % (self._client_first, data, auth_noproof)
        self._auth_message = auth_message

        client_signature = self._hmac(stored_key, auth_message)
        client_proof = base64.b64encode(
            _scram_xor(client_key, client_signature))

        return auth_noproof + (b",p=%s" % client_proof)

    def server_final(self, data: bytes) -> bytes:
        # server-final-message
        pieces = self._get_pieces(data)
        verifier = pieces[b"v"]

        server_key = self._hmac(self._salted_password, b"Server Key")
        server_signature = self._hmac(server_key, self._auth_message)

        if server_signature != base64.b64decode(verifier):
            self.state = SCRAMState.VerifyFailed
            return None
        else:
            self.state = SCRAMState.Success
            return "+"
