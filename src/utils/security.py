import hmac, socket, ssl, typing

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
