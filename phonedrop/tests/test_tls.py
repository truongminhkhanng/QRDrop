from pathlib import Path
import socket
import ssl
import threading
from urllib.request import Request, urlopen

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtendedKeyUsageOID
import pytest

from app import MOBILE_HTML
from core import PhoneDropServer, State
from tls_support import create_tls_context


def test_fresh_certificate_san_fingerprint_and_key_cleanup(tmp_path):
    context, fingerprint, path = create_tls_context('192.168.1.20', tmp_path / 'one')
    cert = x509.load_pem_x509_certificate(path.read_bytes())
    assert str(cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value[0].value) == '192.168.1.20'
    assert cert.fingerprint(hashes.SHA256()).hex().upper() == fingerprint.replace(':', '')
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert not (path.parent / 'private-key.pem').exists()
    assert ExtendedKeyUsageOID.SERVER_AUTH in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    _, second, second_path = create_tls_context('192.168.1.20', tmp_path / 'two')
    assert second != fingerprint
    assert cert.serial_number != x509.load_pem_x509_certificate(second_path.read_bytes()).serial_number


def test_certificate_failure_removes_private_key(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('test failure')
    monkeypatch.setattr(ssl.SSLContext, 'load_cert_chain', fail)
    with pytest.raises(OSError):
        create_tls_context('192.168.1.20', tmp_path)
    assert not (tmp_path / 'private-key.pem').exists()


@pytest.mark.network
def test_real_https_certificate_trust_and_upload(tmp_path):
    context, fingerprint, cert_path = create_tls_context('127.0.0.1', tmp_path / 'tls')
    state = State(tmp_path / 'received')
    server = PhoneDropServer(('127.0.0.1', 0), state, MOBILE_HTML, tls_context=context, allow_loopback=True)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval':.01}, daemon=True)
    thread.start()
    try:
        # Trust only the exact generated certificate for the integration test.
        trusted = ssl.create_default_context(cafile=str(cert_path))
        with urlopen(server.origin + '/?t=' + state.token, context=trusted, timeout=5) as response:
            assert response.status == 200
        sid = state.session.sid
        state.set_state(sid, 'approved')
        headers = {'X-Session':sid, 'Origin':server.origin, 'X-Filename':'tls.txt',
                   'Content-Type':'application/octet-stream'}
        request = Request(server.origin + '/upload', data=b'encrypted', headers=headers, method='POST')
        with urlopen(request, context=trusted, timeout=5) as response:
            assert response.status == 201
        assert (state.folder/'tls.txt').read_bytes() == b'encrypted'
        with socket.create_connection(server.server_address, timeout=3) as raw:
            with trusted.wrap_socket(raw, server_hostname='127.0.0.1') as client:
                certificate = x509.load_der_x509_certificate(client.getpeercert(binary_form=True))
                assert certificate.fingerprint(hashes.SHA256()).hex().upper() == fingerprint.replace(':', '')
        # A fresh self-signed certificate must NOT be silently accepted by default trust.
        with pytest.raises(Exception) as exc:
            urlopen(server.origin + '/', context=ssl.create_default_context(), timeout=5)
        assert 'CERTIFICATE_VERIFY_FAILED' in str(exc.value)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
