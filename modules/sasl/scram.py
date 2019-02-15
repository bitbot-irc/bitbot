import base64, enum, hashlib, hmac, os, typing

# IANA Hash Function Textual Names
# https://tools.ietf.org/html/rfc5802#section-4
# https://www.iana.org/assignments/hash-function-text-names/
# MD2 has been removed as it's unacceptably weak
ALGORITHMS = [
    "MD5", "SHA-1", "SHA-224", "SHA-256", "SHA-384", "SHA-512"]

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
        self.error = ""

        self._client_first = b""
        self._salted_password = b""
        self._auth_message = b""

    def _get_pieces(self, data: bytes) -> typing.Dict[bytes, bytes]:
        pieces = (piece.split(b"=", 1) for piece in data.split(b","))
        return dict((piece[0], piece[1]) for piece in pieces)

    def _hmac(self, key: bytes, msg: bytes) -> bytes:
        return hmac.new(key, msg, self._algo).digest()
    def _hash(self, msg: bytes) -> bytes:
        return hashlib.new(self._algo, msg).digest()

    def _constant_time_compare(self, b1: bytes, b2: bytes):
        return hmac.compare_digest(b1, b2)

    def client_first(self) -> bytes:
        self.state = SCRAMState.ClientFirst
        self._client_first = b"n=%s,r=%s" % (
            _scram_escape(self._username), _scram_nonce())

        # n,,n=<username>,r=<nonce>
        return b"n,,%s" % self._client_first

    def server_first(self, data: bytes) -> bytes:
        self.state = SCRAMState.ClientFinal

        pieces = self._get_pieces(data)
        nonce = pieces[b"r"] # server combines your nonce with it's own
        salt = base64.b64decode(pieces[b"s"]) # salt is b64encoded
        iterations = int(pieces[b"i"])

        salted_password = hashlib.pbkdf2_hmac(self._algo, self._password,
            salt, iterations, dklen=None)
        self._salted_password = salted_password

        client_key = self._hmac(salted_password, b"Client Key")
        stored_key = self._hash(client_key)

        channel = base64.b64encode(b"n,,")
        auth_noproof = b"c=%s,r=%s" % (channel, nonce)
        auth_message = b"%s,%s,%s" % (self._client_first, data, auth_noproof)
        self._auth_message = auth_message

        client_signature = self._hmac(stored_key, auth_message)
        client_proof_xor = _scram_xor(client_key, client_signature)
        client_proof = base64.b64encode(client_proof_xor)

        # c=<b64encode("n,,")>,r=<nonce>,p=<proof>
        return b"%s,p=%s" % (auth_noproof, client_proof)

    def server_final(self, data: bytes) -> bool:
        pieces = self._get_pieces(data)
        if b"e" in pieces:
            self.error = pieces[b"e"].decode("utf8")
            self.state = SCRAMState.Failed
            return False

        verifier = base64.b64decode(pieces[b"v"])

        server_key = self._hmac(self._salted_password, b"Server Key")
        server_signature = self._hmac(server_key, self._auth_message)

        if server_signature == verifier:
            self.state = SCRAMState.Success
            return True
        else:
            self.state = SCRAMState.VerifyFailed
            return False
