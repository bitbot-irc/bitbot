import base64, typing

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.backends import default_backend

    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.hazmat.primitives.serialization import PublicFormat

    has_crypto = True
except ModuleNotFoundError:
    has_crypto = False

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

def public_key(key_filename: str) -> str:
    with open(key_filename, "rb") as key_file:
        cert = x509.load_pem_x509_certificate(key_file.read(),
            default_backend())
    return cert.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("ascii")

def signature(key: PrivateKey, headers: typing.List[typing.Tuple[str, str]]
        ) -> str:
    sign_header_keys = " ".join(h[0].lower() for h in headers)

    sign_string_parts = ["%s: %s" % (k.lower(), v) for k, v in headers]
    sign_string = "\n".join(sign_string_parts)

    signature = key.key.sign(
        sign_string.encode("utf8"),
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    signature = base64.b64encode(signature).decode("ascii")
    return SIGNATURE_FORMAT % (key.id, sign_header_keys, signature)
