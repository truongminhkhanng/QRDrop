"""Ephemeral, self-signed TLS certificate. Private keys never leave the PC."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import ipaddress
import os
from pathlib import Path
import ssl


def create_tls_context(ip: str, directory: Path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    address = ipaddress.IPv4Address(ip)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'PhoneDrop LAN')])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=2))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(address)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
            key_encipherment=False, data_encipherment=False, key_agreement=False,
            key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
        .sign(key, hashes.SHA256()))
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    cert_path = directory / 'certificate.pem'
    key_path = directory / 'private-key.pem'
    # Exclusive creation: never follow/overwrite an existing key path.
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as file:
        file.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
    try:
        with cert_path.open('xb') as file:
            file.write(certificate.public_bytes(serialization.Encoding.PEM))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert_path, key_path)
    finally:
        # OpenSSL holds the key in RAM after load_cert_chain. Remove the disk copy now.
        key_path.unlink(missing_ok=True)
    digest = certificate.fingerprint(hashes.SHA256()).hex().upper()
    fingerprint = ':'.join(digest[index:index + 2] for index in range(0, len(digest), 2))
    return context, fingerprint, cert_path
