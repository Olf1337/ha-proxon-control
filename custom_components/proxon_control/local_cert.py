"""The certificate for the direct connection in the home network, fetched once from the Proxon portal.

The unit only accepts clients with a certificate signed by the Proxon portal. Like the original app on its first login, a key
is made on this computer, a signing request for "user-<Device ID>@phc.proxon.de" is sent to the portal together with the
Device ID's password, and the portal answers with the signed certificate. That is the only contact with the portal; the
certificate is kept (with its key) in Home Assistant's config folder and used from then on. The key never leaves this computer.
(Procedure as documented by the ha-lan-proxon project, MIT licence - see THIRD_PARTY_NOTICES.md.)
No Home Assistant imports; blocking.
"""
from __future__ import annotations

import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from .local import fingerprint, user_email

_LOGGER = logging.getLogger(__name__)

PORTAL_SIGN_URL = "https://lscontrol.nabto.com/service/register"
KEY_BITS = 1024  # as the original app; the portal signs these (the key only identifies, the home network data is not encrypted)
CERT_FILE = "certificate.pem"
KEY_FILE = "key.pem"
BEGIN, END = "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----"


class CertificateError(Exception):
    """The certificate could not be fetched (portal not reachable or unexpected answer)."""


class PortalRejected(CertificateError):
    """The portal refused the Device ID / password."""


def _folder(storage_dir: str, device_id: str) -> str:
    return os.path.join(storage_dir, "local", device_id.strip())


def load(storage_dir: str, device_id: str) -> str | None:
    """The stored certificate (PEM) for this Device ID, if there is one."""
    path = os.path.join(_folder(storage_dir, device_id), CERT_FILE)
    try:
        with open(path, encoding="ascii") as f:
            pem = f.read()
        fingerprint(pem)  # readable?
        return pem
    except (OSError, ValueError):
        return None


def _key_and_request(email: str) -> tuple[str, str]:
    # imported here: only needed once, when the certificate is fetched
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=KEY_BITS)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.EMAIL_ADDRESS, email)]))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()).decode()
    return key_pem, csr.public_bytes(serialization.Encoding.PEM).decode()


def parse_answer(body: str) -> str:
    """The certificate from the portal's answer: lines "status", "message", then the PEM certificate. Status 0 = signed."""
    lines = body.splitlines()
    status = lines[0].strip() if lines else ""
    if status != "0":
        message = lines[1].strip() if len(lines) > 1 else ""
        raise PortalRejected(message or f"portal error {status or '?'}")
    if BEGIN not in body or END not in body:
        raise CertificateError("the portal's answer holds no certificate")
    return body[body.index(BEGIN):body.index(END) + len(END)] + "\n"


def fetch(storage_dir: str, device_id: str, password: str, timeout: float = 30) -> str:
    """Have the portal sign a new certificate, store it with its key and return it (PEM)."""
    email = user_email(device_id)
    key_pem, csr_pem = _key_and_request(email)
    data = urllib.parse.urlencode({"password": password, "email": email, "csr": csr_pem}).encode()
    req = urllib.request.Request(PORTAL_SIGN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https address of the portal
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        raise CertificateError(f"the portal answered HTTP {err.code}") from err
    except (urllib.error.URLError, OSError) as err:
        raise CertificateError(f"the portal is not reachable: {err}") from err
    cert_pem = parse_answer(body)
    folder = _folder(storage_dir, device_id)
    os.makedirs(folder, exist_ok=True)
    key_path = os.path.join(folder, KEY_FILE)
    with open(key_path, "w", encoding="ascii") as f:
        f.write(key_pem)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    with open(os.path.join(folder, CERT_FILE), "w", encoding="ascii") as f:
        f.write(cert_pem)
    _LOGGER.info("Certificate for the direct connection fetched from the Proxon portal")
    return cert_pem


def ensure(storage_dir: str, device_id: str, password: str) -> str:
    """The stored certificate, or a newly fetched one."""
    return load(storage_dir, device_id) or fetch(storage_dir, device_id, password)


def age(storage_dir: str, device_id: str) -> float | None:
    """Seconds since the stored certificate was fetched (None without one)."""
    try:
        return time.time() - os.path.getmtime(os.path.join(_folder(storage_dir, device_id), CERT_FILE))
    except OSError:
        return None


def forget(storage_dir: str, device_id: str) -> None:
    """Delete the stored certificate (e.g. when the unit no longer accepts it), so a new one is fetched."""
    for name in (CERT_FILE, KEY_FILE):
        try:
            os.remove(os.path.join(_folder(storage_dir, device_id), name))
        except OSError:
            pass
