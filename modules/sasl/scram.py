import base64, enum, hashlib, hmac, os, typing

# IANA Hash Function Textual Names
# https://tools.ietf.org/html/rfc5802#section-4
# https://www.iana.org/assignments/hash-function-text-names/
ALGORITHMS = [
    "MD2", "MD5", "SHA-1", "SHA-224", "SHA-256", "SHA-384", "SHA-512"]

def _scram_nonce() -> bytes:
    return base64.b64encode(os.urandom(32))
def _scram_escape(s: bytes) -> bytes:
    return s.replace(b"=", b"=3D").replace(b",", b"=2C")
def _scram_unescape(s: bytes) -> bytes:
    return s.replace(b"=3D", b"=").replace(b"=2C", b",")
def _scram_xor(s1: bytes, s2: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(s1, s2))

class SCRAMState(enum.Enum):
    Uninitialised = 0
    ClientFirst = 1
    ClientFinal = 2
    Success = 3
    Failed = 4
    VerifyFailed = 5

class SCRAMError(Exception):
    pass

class SCRAM(object):
    def __init__(self, algo: str, username: str, password: str):
        if not algo in ALGORITHMS:
            raise ValueError("Unknown SCRAM algorithm '%s'" % algo)

        self._algo = algo.replace("-", "") # SHA-1 -> SHA1
        self._username = username.encode("utf8")
        self._password = password.encode("utf8")

        self.state = SCRAMState.Uninitialised
        self.error = None # typing.Optional[str]

        self._client_first = None # typing.Optional[bytes]
        self._salted_password = None # typing.Optional[bytes]
        self._auth_message = None # typing.Optional[bytes]

    def _get_pieces(self, data: bytes) -> typing.Dict[bytes, bytes]:
        pieces = (piece.split(b"=", 1) for piece in data.split(b","))
        return dict((piece[0], piece[1]) for piece in pieces)

    def _hmac(self, key: bytes, msg: bytes) -> bytes:
        return hmac.digest(key, msg, self._algo)
    def _hash(self, msg: bytes) -> bytes:
        return hashlib.new(self._algo, msg).digest()

    def client_first(self) -> bytes:
        self.state = SCRAMState.ClientFirst
        self._client_first = b"n=%s,r=%s" % (
            _scram_escape(self._username), _scram_nonce())
        return b"n,,%s" % self._client_first

    def server_first(self, data: bytes) -> bytes:
        self.state = SCRAMState.ClientFinal

        pieces = self._get_pieces(data)
        nonce = pieces[b"r"]
        salt = base64.b64decode(pieces[b"s"])
        iterations = pieces[b"i"]

        self._salted_password = hashlib.pbkdf2_hmac(self._algo, self._password,
            salt, int(iterations), dklen=None)

        client_key = self._hmac(self._salted_password, b"Client Key")
        stored_key = self._hash(client_key)

        channel = base64.b64encode(b"n,,")
        auth_noproof = b"c=%s,r=%s" % (channel, nonce)
        self._auth_message = b"%s,%s,%s" % (
            self._client_first, data, auth_noproof)

        client_signature = self._hmac(stored_key, self._auth_message)
        client_proof = base64.b64encode(
            _scram_xor(client_key, client_signature))

        return auth_noproof + (b",p=%s" % client_proof)

    def server_final(self, data: bytes) -> bool:
        pieces = self._get_pieces(data)
        if b"e" in pieces:
            self.error = pieces[b"e"].decode("utf8")
            self.state = SCRAMState.Failed
            return False

        verifier = pieces[b"v"]

        server_key = self._hmac(self._salted_password, b"Server Key")
        server_signature = self._hmac(server_key, self._auth_message)

        if server_signature != base64.b64decode(verifier):
            self.state = SCRAMState.VerifyFailed
            return False
        else:
            self.state = SCRAMState.Success
            return True
