import base64, typing
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

SIGNATURE_FORMAT = (
    "keyId=\"%s\",headers=\"%s\",signature=\"%s\",algorithm=\"rsa-sha256\"")


def _private_key(key_filename: str) -> rsa.RSAPrivateKey:
    with open(key_filename, "rb") as key_file:
        return serialization.load_pem_private_key(
            key_file.read(), password=None, backend=default_backend())

class PrivateKey(object):
    def __init__(self, filename, id):
        self.key = _private_key(filename)
        self.id = id

def signature(key: PrivateKey, headers: typing.List[typing.Tuple[str, str]]
        ) -> str:
    sign_header_keys = " ".join(h[0] for h in headers)

    sign_string_parts = ["%s: %s" % (k, v) for k, v in headers]
    sign_string = "\n".join(sign_string_parts)

    signature = key.key.sign(
        sign_string.encode("utf8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )

    signature = base64.b64encode(signature).decode("ascii")
    return SIGNATURE_FORMAT % (key.id, sign_header_keys, signature)
