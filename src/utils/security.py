import base64, hmac, socket, ssl, typing

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

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

def a_encrypt(key_filename: str, data: str):
    with open(key_filename, "rb") as key_file:
        key_content = key_file.read()
    key = serialization.load_pem_public_key(
        key_content, backend=default_backend())
    out = key.encrypt(data.encode("utf8"), padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(), label=None))
    return base64.b64encode(out).decode("iso-8859-1")

def a_decrypt(key_filename: str, data: str):
    with open(key_filename, "rb") as key_file:
        key_content = key_file.read()
    key = serialization.load_pem_private_key(
        key_content, password=None, backend=default_backend())
    out = key.decrypt(base64.b64decode(data), padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(), label=None))
    return out.decode("utf8")
