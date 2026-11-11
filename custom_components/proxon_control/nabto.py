"""Minimal ctypes binding to the Nabto 4 client library, used the way the original app uses it.

Login (from the original app's native module):
  1. set option urlPortalHostName = "lscontrol"
  2. open a session for "user-<Device ID>@phc.proxon.de" with the appliance password
  3. if that fails, create the profile on the portal with the same user/password and open again
  4. load the device's query interface, then call queries with nabtoRpcInvoke

This file has no Home Assistant imports so the add-on can use the same code.
"""
from __future__ import annotations

import ctypes
import hashlib
import io
import json
import os
import platform
import re
import select
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile

PORTAL_HOST = "lscontrol"
DEVICE_DOMAIN = ".remote.lscontrol.dk"

# The library comes from Nabto's own command line tool release (Nabto client SDK 4.9.11).
LIB_RELEASES = {
    ("linux", "x86_64"): (
        "https://github.com/nabto/nabto-cli/releases/download/v1.3.0/nabto-cli-linux.zip",
        "nabto-cli-linux/libnabto_client_api.so",
        "libnabto_client_api.so",
    ),
    ("darwin", "arm64"): (
        "https://github.com/nabto/nabto-cli/releases/download/v1.3.0/nabto-cli-osx.zip",
        "nabto-cli-osx/libnabto_client_api.dylib",
        "libnabto_client_api.dylib",
    ),
}
# SHA-256 of the library files inside those releases (checked after download)
LIB_SHA256 = {
    "libnabto_client_api.dylib": "b7c434cbe081998b4c8e571ffed4d52973396febd6ccdbb9ec91512d31a63714",
    "libnabto_client_api.so": "0064adf473c142259ad2cff3f1010f880f3c6cdfc92737957f9510426f57d036",
}

# Home Assistant OS runs on Alpine Linux (musl) and can't load Nabto's glibc-only library directly.
# A small helper program (bin/proxon-nabto-helper-linux-x86_64) is started through Debian's glibc loader instead.
DEBIAN_POOL = "https://deb.debian.org/debian/pool/main/"
RUNTIME_PACKAGES = [
    # (directory in the pool, package, pinned file name, pinned SHA-256, newest-version pattern, {file in package: name here})
    ("g/glibc/", "libc6", "libc6_2.36-9+deb12u14_amd64.deb",
     "ba4f88f73dbc3ae9055f3c20f4523bfdbaf1ad13ff95e258924f77d20b4fbedf",
     r"libc6_2\.36-9\+deb12u\d+_amd64\.deb",
     {"lib/x86_64-linux-gnu/ld-linux-x86-64.so.2": "ld-linux-x86-64.so.2", "lib/x86_64-linux-gnu/libc.so.6": "libc.so.6",
      "lib/x86_64-linux-gnu/libm.so.6": "libm.so.6", "lib/x86_64-linux-gnu/libdl.so.2": "libdl.so.2",
      "lib/x86_64-linux-gnu/libpthread.so.0": "libpthread.so.0", "lib/x86_64-linux-gnu/librt.so.1": "librt.so.1",
      "lib/x86_64-linux-gnu/libresolv.so.2": "libresolv.so.2"}),
    ("g/gcc-12/", "libstdc++6", "libstdc++6_12.2.0-14+deb12u1_amd64.deb",
     "5cd3171216d4ab0fc911cfe9c35509bf2dd8f47761c43b7f6a4296701551a24d",
     r"libstdc\+\+6_12\.2\.0-14\+deb12u\d+_amd64\.deb",
     {"usr/lib/x86_64-linux-gnu/libstdc++.so.6": "libstdc++.so.6"}),
    ("g/gcc-12/", "libgcc-s1", "libgcc-s1_12.2.0-14+deb12u1_amd64.deb",
     "3016e62cb4b7cd8038822870601f5ed131befe942774d0f745622cc77d8a88f7",
     r"libgcc-s1_12\.2\.0-14\+deb12u\d+_amd64\.deb",
     {"lib/x86_64-linux-gnu/libgcc_s.so.1": "libgcc_s.so.1"}),
]
HELPER_FILE = "bin/proxon-nabto-helper-linux-x86_64"

# Nabto 4 status codes (nabto_client_api.h)
STATUS_NAMES = [
    "OK", "NO_PROFILE", "ERROR_READING_CONFIG", "API_NOT_INITIALIZED", "INVALID_SESSION",
    "OPEN_CERT_OR_PK_FAILED", "UNLOCK_PK_FAILED", "PORTAL_LOGIN_FAILURE", "CERT_SIGNING_ERROR",
    "CERT_SAVING_FAILURE", "ADDRESS_IN_USE", "INVALID_ADDRESS", "NO_NETWORK", "CONNECT_TO_HOST_FAILED",
    "STREAMING_UNSUPPORTED", "INVALID_STREAM", "DATA_PENDING", "BUFFER_FULL", "FAILED", "INVALID_TUNNEL",
    "ILLEGAL_PARAMETER", "INVALID_RESOURCE", "INVALID_STREAM_OPTION", "INVALID_STREAM_OPTION_ARGUMENT",
    "ABORTED", "STREAM_CLOSED", "FAILED_WITH_JSON_MESSAGE", "RPC_INTERFACE_NOT_SET", "RPC_NO_SUCH_REQUEST",
    "RPC_DEVICE_OFFLINE", "RPC_RESPONSE_DECODE_FAILURE", "RPC_COMMUNICATION_PROBLEM", "NO_SUCH_KEY",
]
OK = 0
FAILED_WITH_JSON_MESSAGE = 26

# Query interface of the ventilation controller (ids, names and field types as the device expects them).
INTERFACE_XML = """<?xml version="1.0"?>
<unabto_queries>
  <query id="42" name="setpointReadListValue.json">
    <request><list name="list"><parameter name="obj" type="uint8"/><parameter name="address" type="uint16"/></list></request>
    <response format="json"><parameter name="status" type="uint8"/><list name="data"><parameter name="value" type="int16"/></list></response>
  </query>
  <query id="43" name="setpointWriteValue.json">
    <request><list name="list"><parameter name="obj" type="uint8"/><parameter name="address" type="uint32"/><parameter name="value" type="uint16"/></list></request>
    <response format="json"><parameter name="status" type="uint8"/></response>
  </query>
  <query id="45" name="datapointReadListValue.json">
    <request><list name="list"><parameter name="obj" type="uint8"/><parameter name="address" type="uint32"/></list></request>
    <response format="json"><list name="data"><parameter name="value" type="int16"/></list></response>
  </query>
</unabto_queries>
"""


class NabtoError(Exception):
    """Raised for a failed Nabto call; `status` is the Nabto status code (or -1)."""

    def __init__(self, message: str, status: int = -1) -> None:
        super().__init__(message)
        self.status = status


def log_errors(home: str, limit: int = 2) -> str:
    """The last error lines of Nabto's own log file in the home folder (it says what went wrong for 'unspecified' errors)."""
    try:
        with open(os.path.join(home, "logs", "nabto-api-log.txt"), "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 20000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    found: list[str] = []
    for line in lines:
        if ",error]" in line or ",warn_]" in line and "root" in line:
            msg = line.split("): ", 1)[-1].strip()
            if msg and msg not in found and "static resource dir not found" not in msg:
                found.append(msg)
    return " | ".join(found[-limit:])


def status_name(code: int) -> str:
    return STATUS_NAMES[code] if 0 <= code < len(STATUS_NAMES) else str(code)


def user_name(device_id: str) -> str:
    return f"user-{device_id.strip()}@phc.proxon.de"


def platform_key() -> tuple[str, str]:
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    return sys.platform if sys.platform != "linux2" else "linux", machine


def library_supported() -> bool:
    return platform_key() in LIB_RELEASES


def ensure_library(directory: str) -> str:
    """Return the path of the client library in `directory`, downloading it on first use."""
    key = platform_key()
    if key not in LIB_RELEASES:
        raise NabtoError(
            f"Die Nabto-Bibliothek gibt es nicht für dieses System ({key[0]}/{key[1]}). "
            "Bitte das Proxon-Bridge-Add-on verwenden."
        )
    url, member, name = LIB_RELEASES[key]
    path = os.path.join(directory, name)
    if os.path.exists(path):
        return path
    os.makedirs(directory, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 - fixed https URL
        data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        blob = z.read(member)
    want = LIB_SHA256.get(name)
    if want and hashlib.sha256(blob).hexdigest() != want:
        raise NabtoError("Die heruntergeladene Nabto-Bibliothek hat eine unerwartete Prüfsumme.")
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, path)
    return path


def rpc_url(device: str, query: str, request: dict) -> str:
    params = json.dumps({"request": request} if "request" not in request else request, separators=(",", ":"))
    return f"nabto://{device}{DEVICE_DOMAIN}/{query}.json?json={params}"


def parse_rpc(status: int, text: str) -> dict:
    """Turn a reply of nabtoRpcInvoke into a dict or raise NabtoError."""
    if status not in (OK, FAILED_WITH_JSON_MESSAGE):
        raise NabtoError(f"Gerät nicht erreichbar ({status_name(status)})", status)
    try:
        data = json.loads(text) if text else {}
    except ValueError as err:
        raise NabtoError("Ungültige Antwort vom Gerät") from err
    if isinstance(data, dict) and data.get("error"):
        e = data["error"]
        raise NabtoError(str(e.get("body") or e.get("detail") or e) if isinstance(e, dict) else str(e), status)
    return data


class NabtoClient:
    """One logged-in session to one appliance. Not thread-safe by itself; calls are serialised."""

    _startup_lock = threading.Lock()
    _started: dict[str, ctypes.CDLL] = {}

    def __init__(self, library_path: str, home_dir: str) -> None:
        self._lock = threading.Lock()
        with NabtoClient._startup_lock:
            lib = NabtoClient._started.get(library_path)
            if lib is None:
                try:
                    lib = ctypes.CDLL(library_path)
                except OSError as err:
                    raise NabtoError(f"Nabto-Bibliothek lässt sich nicht laden: {err}") from err
                self._declare(lib)
                os.makedirs(home_dir, exist_ok=True)
                st = lib.nabtoStartup(home_dir.encode())
                if st != OK:
                    raise NabtoError(f"Nabto-Start fehlgeschlagen ({status_name(st)})", st)
                # like the original app: install Nabto's root certificates; without them the signed login certificate
                # can't be verified and opening the session fails with "unspecified error" (18)
                st = lib.nabtoInstallDefaultStaticResources(None)
                if st != OK:
                    raise NabtoError(f"Nabto-Zertifikate konnten nicht installiert werden ({status_name(st)})", st)
                lib.nabtoSetOption(b"urlPortalHostName", PORTAL_HOST.encode())
                NabtoClient._started[library_path] = lib
        self._lib = lib
        self._home = home_dir
        self._session = ctypes.c_void_p()
        self._device = ""

    @staticmethod
    def _declare(lib: ctypes.CDLL) -> None:
        cp = ctypes.c_char_p
        pp = ctypes.POINTER(ctypes.c_void_p)
        lib.nabtoStartup.argtypes = [cp]
        lib.nabtoSetOption.argtypes = [cp, cp]
        lib.nabtoOpenSession.argtypes = [pp, cp, cp]
        lib.nabtoCreateProfile.argtypes = [cp, cp]
        lib.nabtoCloseSession.argtypes = [ctypes.c_void_p]
        lib.nabtoRpcSetDefaultInterface.argtypes = [ctypes.c_void_p, cp, pp]
        lib.nabtoRpcInvoke.argtypes = [ctypes.c_void_p, cp, pp]
        lib.nabtoInstallDefaultStaticResources.argtypes = [cp]
        lib.nabtoFree.argtypes = [ctypes.c_void_p]
        for fn in ("nabtoStartup", "nabtoSetOption", "nabtoOpenSession", "nabtoCreateProfile",
                   "nabtoCloseSession", "nabtoRpcSetDefaultInterface", "nabtoRpcInvoke", "nabtoFree",
                   "nabtoInstallDefaultStaticResources"):
            getattr(lib, fn).restype = ctypes.c_int

    def _take_string(self, ptr: ctypes.c_void_p) -> str:
        if not ptr.value:
            return ""
        text = ctypes.string_at(ptr.value).decode("utf-8", "replace")
        self._lib.nabtoFree(ptr)
        return text

    def login(self, device_id: str, password: str) -> None:
        """Open a session the way the original app does (create the profile when needed)."""
        user = user_name(device_id).encode()
        pw = password.encode()
        with self._lock:
            self.close()
            st = self._lib.nabtoOpenSession(ctypes.byref(self._session), user, pw)
            if st != OK:
                created = self._lib.nabtoCreateProfile(user, pw)
                if created != OK:
                    raise NabtoError(f"Anmeldung fehlgeschlagen ({status_name(created)}) {log_errors(self._home)}".strip(), created)
                st = self._lib.nabtoOpenSession(ctypes.byref(self._session), user, pw)
                if st != OK:
                    raise NabtoError(f"Sitzung konnte nicht geöffnet werden ({status_name(st)}) {log_errors(self._home)}".strip(), st)
            err = ctypes.c_void_p()
            st = self._lib.nabtoRpcSetDefaultInterface(self._session, INTERFACE_XML.encode(), ctypes.byref(err))
            msg = self._take_string(err)
            if st != OK:
                raise NabtoError(f"Schnittstelle nicht akzeptiert ({status_name(st)}) {msg}", st)
            self._device = device_id.strip()

    def invoke(self, query: str, request: dict) -> dict:
        """Run one query, e.g. invoke("setpointReadListValue", {"list": [...]})."""
        url = rpc_url(self._device, query, request)
        out = ctypes.c_void_p()
        with self._lock:
            if not self._session.value:
                raise NabtoError("Nicht angemeldet", 4)
            st = self._lib.nabtoRpcInvoke(self._session, url.encode(), ctypes.byref(out))
            text = self._take_string(out)
        return parse_rpc(st, text)

    def close(self) -> None:
        if self._session.value:
            self._lib.nabtoCloseSession(self._session)
            self._session = ctypes.c_void_p()


# ---------------- glibc runtime + helper process (Home Assistant OS / Alpine) ----------------


def is_musl() -> bool:
    """True on Alpine and other musl systems, where Nabto's glibc library can't be loaded directly."""
    if not sys.platform.startswith("linux"):
        return False
    return any(os.path.exists(p) for p in ("/lib/ld-musl-x86_64.so.1", "/lib/ld-musl-aarch64.so.1")) or (
        platform.libc_ver()[0] != "glibc"
    )


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310 - fixed https URL
        return resp.read()


def _ar_members(data: bytes):
    """Members of a .deb file (an ar archive)."""
    if data[:8] != b"!<arch>\n":
        raise NabtoError("Ungültiges Debian-Paket")
    pos = 8
    while pos + 60 <= len(data):
        hdr = data[pos:pos + 60]
        name = hdr[:16].decode().strip().rstrip("/")
        size = int(hdr[48:58].decode().strip())
        yield name, data[pos + 60:pos + 60 + size]
        pos += 60 + size + (size & 1)


def extract_deb(deb: bytes, wanted: dict[str, str], directory: str) -> None:
    """Write the wanted files (path inside the package -> file name here) into `directory`."""
    data = next((m for n, m in _ar_members(deb) if n.startswith("data.tar")), None)
    if data is None:
        raise NabtoError("Debian-Paket ohne Daten")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
        members = {m.name.lstrip("./"): m for m in tf.getmembers()}
        for src, dst in wanted.items():
            m = members.get(src)
            for _ in range(8):  # follow links inside the package
                if m is None or not (m.issym() or m.islnk()):
                    break
                target = m.linkname if m.islnk() else os.path.normpath(os.path.join(os.path.dirname(m.name.lstrip("./")), m.linkname))
                m = members.get(target.lstrip("./"))
            if m is None or not m.isfile():
                raise NabtoError(f"{src} fehlt im Debian-Paket")
            tmp = os.path.join(directory, dst + ".part")
            extracted = tf.extractfile(m)
            if extracted is None:
                raise NabtoError(f"{src} fehlt im Debian-Paket")
            with open(tmp, "wb") as f:
                f.write(extracted.read())
            os.replace(tmp, os.path.join(directory, dst))


def _fetch_deb(directory_in_pool: str, pinned: str, sha256: str, pattern: str) -> bytes:
    """The pinned package; if Debian has replaced it by a security update, the newest one of the same release."""
    try:
        blob = _download(DEBIAN_POOL + directory_in_pool + pinned)
        if hashlib.sha256(blob).hexdigest() != sha256:
            raise NabtoError("Ein heruntergeladenes Debian-Paket hat eine unerwartete Prüfsumme.")
        return blob
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
    listing = _download(DEBIAN_POOL + directory_in_pool).decode("utf-8", "replace")
    names = sorted(set(re.findall(pattern, listing)), key=lambda n: [int(x) for x in re.findall(r"\d+", n.split("deb12u")[-1])])
    if not names:
        raise NabtoError("Kein passendes Debian-Paket gefunden.")
    return _download(DEBIAN_POOL + directory_in_pool + names[-1])


def ensure_runtime(directory: str) -> str:
    """glibc loader + libraries from Debian 12 (amd64) in `directory`, downloaded on first use."""
    marker = os.path.join(directory, ".complete")
    if not os.path.exists(marker):
        os.makedirs(directory, exist_ok=True)
        for pool_dir, _name, pinned, sha, pattern, wanted in RUNTIME_PACKAGES:
            extract_deb(_fetch_deb(pool_dir, pinned, sha, pattern), wanted, directory)
        with open(marker, "w", encoding="utf-8") as f:
            f.write("ok\n")
    # the loader is started like a program, so it needs the "executable" permission (older downloads were saved without it)
    make_executable(os.path.join(directory, LOADER))
    return directory


LOADER = "ld-linux-x86-64.so.2"


def make_executable(path: str) -> None:
    try:
        os.chmod(path, os.stat(path).st_mode | 0o755)
    except OSError:
        pass


def helper_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), HELPER_FILE)


class HelperClient:
    """Same interface as NabtoClient, but the library runs in a helper process started through Debian's glibc loader."""

    def __init__(self, directory: str, argv: list[str] | None = None, lib_path: str | None = None) -> None:
        self._dir = directory
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._buf = b""
        self._device = ""
        self._log_path = os.path.join(directory, "helper.log")
        os.makedirs(directory, exist_ok=True)
        self._lib = lib_path or ensure_library(os.path.join(directory, "lib"))
        self._runtime: str | None = None
        self._helper: str | None = None
        self._relocated = False
        if argv is None:
            runtime = ensure_runtime(os.path.join(directory, "runtime"))
            helper = helper_path()
            if not os.path.exists(helper):
                raise NabtoError("Das Hilfsprogramm fehlt in der Integration (bin/proxon-nabto-helper-linux-x86_64).")
            self._runtime, self._helper = runtime, helper
            argv = [os.path.join(runtime, LOADER), "--library-path", runtime, helper]
            self._env = dict(os.environ, LD_LIBRARY_PATH=runtime)
        else:
            self._env = dict(os.environ)
        self._argv = argv

    def _relocate(self) -> bool:
        """Some systems don't allow running programs from the config folder ("noexec"). Copy everything the helper needs
        to another folder (temporary folder, /dev/shm, /run) and use that one instead. Returns True if a folder worked."""
        if self._relocated or self._runtime is None or self._helper is None:
            return False
        self._relocated = True
        # mkdtemp makes a new folder only this user can read, so these shared places are safe to use
        for base in dict.fromkeys([tempfile.gettempdir(), "/dev/shm", "/run"]):  # nosec B108
            try:
                dest = tempfile.mkdtemp(prefix="proxon_rt_", dir=base)
                rt = os.path.join(dest, "runtime")
                shutil.copytree(self._runtime, rt)
                helper = os.path.join(dest, "helper")
                shutil.copy2(self._helper, helper)
                lib = os.path.join(dest, os.path.basename(self._lib))
                shutil.copy2(self._lib, lib)
                for p in (os.path.join(rt, LOADER), helper, lib):
                    make_executable(p)
                argv = [os.path.join(rt, LOADER), "--library-path", rt, helper]
                if self._probe(argv, dict(os.environ, LD_LIBRARY_PATH=rt)):
                    self._argv, self._env, self._lib = argv, dict(os.environ, LD_LIBRARY_PATH=rt), lib
                    return True
            except OSError:
                continue
        return False

    def _probe(self, argv: list[str], env: dict) -> bool:
        """Start the helper once and ask for its version."""
        try:
            proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
                argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env
            )
        except OSError:
            return False
        try:
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(b'{"cmd":"version"}\n')
            proc.stdin.flush()
            ready, _, _ = select.select([proc.stdout.fileno()], [], [], 10)
            if not ready:
                return False
            line = os.read(proc.stdout.fileno(), 4096).split(b"\n", 1)[0]
            return json.loads(line).get("ok") is True
        except (OSError, ValueError, AttributeError):
            return False
        finally:
            proc.kill()
            for pipe in (proc.stdin, proc.stdout):
                try:
                    if pipe:
                        pipe.close()
                except OSError:
                    pass
            proc.wait()

    # -- process handling --
    def _log_tail(self) -> str:
        try:
            with open(self._log_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                f.seek(max(0, f.tell() - 600))
                return f.read().decode("utf-8", "replace").strip()
        except OSError:
            return ""

    def _start(self) -> None:
        with open(self._log_path, "ab") as log:
            try:
                self._proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
                    self._argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, env=self._env, cwd=self._dir
                )
            except OSError as err:
                raise NabtoError(f"Hilfsprogramm lässt sich nicht starten: {err}") from err
        self._buf = b""

    def _stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None:
            try:
                proc.kill()
            except OSError:
                pass
            for pipe in (proc.stdin, proc.stdout):
                try:
                    if pipe:
                        pipe.close()
                except OSError:
                    pass
            proc.wait()

    def _call(self, req: dict, timeout: float) -> dict:
        try:
            return self._call_once(req, timeout)
        except NabtoError as err:
            text = str(err)
            blocked = any(s in text for s in ("Permission denied", "failed to map segment", "Operation not permitted"))
            if blocked and self._relocate():
                if "lib" in req:  # the library may have moved too
                    req = dict(req, lib=self._lib)
                return self._call_once(req, timeout)
            raise

    def _call_once(self, req: dict, timeout: float) -> dict:
        if self._proc is None or self._proc.poll() is not None:
            self._stop()
            self._start()
        proc = self._proc
        assert proc is not None and proc.stdin is not None and proc.stdout is not None
        try:
            proc.stdin.write((json.dumps(req) + "\n").encode())
            proc.stdin.flush()
        except OSError as err:
            self._stop()
            raise NabtoError(f"Hilfsprogramm antwortet nicht: {err} {self._log_tail()}".strip()) from err
        fd = proc.stdout.fileno()
        deadline = time.monotonic() + timeout
        while b"\n" not in self._buf:
            left = deadline - time.monotonic()
            if left <= 0:
                self._stop()
                raise NabtoError("Zeitüberschreitung bei der Verbindung zum Gerät")
            ready, _, _ = select.select([fd], [], [], left)
            if not ready:
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                self._stop()
                raise NabtoError(f"Hilfsprogramm wurde beendet. {self._log_tail()}".strip())
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\n")
        try:
            return json.loads(line)
        except ValueError as err:
            self._stop()
            raise NabtoError("Ungültige Antwort vom Hilfsprogramm") from err

    def _check(self, reply: dict, what: str) -> dict:
        if not reply.get("ok"):
            st = reply.get("status", -1)
            why = log_errors(os.path.join(self._dir, "home"))
            raise NabtoError(f"{what} ({status_name(st) if isinstance(st, int) else st}) {reply.get('error', '')} {why}".strip(), st if isinstance(st, int) else -1)
        return reply

    # -- same interface as NabtoClient --
    def check(self) -> None:
        """Load the library and the query interface without logging in."""
        with self._lock:
            self._check(self._call({"cmd": "check", "lib": self._lib, "home": os.path.join(self._dir, "home"), "interface": INTERFACE_XML}, 60), "Nabto-Bibliothek lässt sich nicht verwenden")

    def login(self, device_id: str, password: str) -> None:
        with self._lock:
            self._check(
                self._call(
                    {"cmd": "login", "lib": self._lib, "home": os.path.join(self._dir, "home"), "user": user_name(device_id),
                     "password": password, "interface": INTERFACE_XML},
                    120,
                ),
                "Anmeldung fehlgeschlagen",
            )
            self._device = device_id.strip()

    def invoke(self, query: str, request: dict) -> dict:
        url = rpc_url(self._device, query, request)
        with self._lock:
            reply = self._call({"cmd": "invoke", "url": url}, 60)
        if not reply.get("ok"):
            raise NabtoError(f"Gerät nicht erreichbar ({reply.get('error', '')})", reply.get("status", -1))
        return parse_rpc(int(reply.get("status", OK)), reply.get("json", ""))

    def close(self) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._call({"cmd": "close"}, 5)
                except NabtoError:
                    pass
            self._stop()


def direct_load_works(library_path: str) -> bool:
    try:
        ctypes.CDLL(library_path)
        return True
    except OSError:
        return False


def create_client(directory: str):
    """The way to reach the library on this system: directly (glibc Linux, macOS) or through the helper (Alpine)."""
    key = platform_key()
    lib = ensure_library(os.path.join(directory, "lib"))
    if key == ("linux", "x86_64") and (is_musl() or not direct_load_works(lib)):
        return HelperClient(directory, lib_path=lib)
    return NabtoClient(lib, os.path.join(directory, "home"))
