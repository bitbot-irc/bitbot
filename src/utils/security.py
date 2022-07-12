import base64, binascii, hmac, os, socket, ssl, typing

def ssl_context(cert: str=None, key: str=None, verify: bool=True
        ) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.load_default_certs()

    if verify:
        context.verify_mode = ssl.CERT_REQUIRED
    if cert and key:
        context.load_cert_chain(cert, keyfile=key)

    return context

def ssl_wrap(sock: socket.socket, cert: str=None, key: str=None,
        verify: bool=True, server_side: bool=False, hostname: str=None
        ) -> ssl.SSLSocket:
    context = ssl_context(cert=cert, key=key, verify=verify)
    return context.wrap_socket(sock, server_side=server_side,
        server_hostname=hostname)

def constant_time_compare(a: typing.AnyStr, b: typing.AnyStr) -> bool:
    return hmac.compare_digest(a, b)

import hashlib
def password(byte_n: int=32) -> str:
    return binascii.hexlify(os.urandom(byte_n)).decode("utf8")
def salt(byte_n: int=64) -> str:
    return base64.b64encode(os.urandom(byte_n)).decode("utf8")
def hash(given_salt: str, data: str):
    hash = hashlib.scrypt(
        data.encode("utf8"),
        salt=given_salt.encode("utf8"),
        n=1<<14,
        r=8,
        p=1
    )
    return base64.b64encode(hash).decode("ascii")
def hash_verify(salt: str, data: str, compare: str):
    given_hash = hash(salt, data)
    return constant_time_compare(given_hash, compare)

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as a_padding

def rsa_encrypt(key_filename: str, data: bytes) -> str:
    with open(key_filename, "rb") as key_file:
        key_content = key_file.read()
    key = serialization.load_pem_public_key(
        key_content, backend=default_backend())
    out = key.encrypt(data, a_padding.OAEP(
        mgf=a_padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(), label=None))
    return base64.b64encode(out).decode("latin-1")

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

def aes_key() -> bytes:
    return os.urandom(32)
def aes_encrypt(key: bytes, data: str) -> str:
    iv = os.urandom(16)
    padder = padding.PKCS7(256).padder()

    data_bytes = padder.update(data.encode("utf8"))+padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv),
        backend=default_backend()).encryptor()

    ct = encryptor.update(data_bytes)+encryptor.finalize()
    return base64.b64encode(iv+ct).decode("latin-1")
