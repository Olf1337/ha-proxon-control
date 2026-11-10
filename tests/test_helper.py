"""The helper-process path used on Home Assistant OS (Alpine): protocol, error handling and runtime unpacking."""
from __future__ import annotations

import io
import json
import lzma
import os
import sys
import tarfile
import textwrap

import pytest

from custom_components.proxon_control import nabto
from custom_components.proxon_control.nabto import HelperClient, NabtoError

FAKE_HELPER = textwrap.dedent(
    '''
    import json, sys
    session = False
    for line in sys.stdin:
        req = json.loads(line)
        cmd = req["cmd"]
        if cmd == "login":
            if req["password"] == "bad":
                out = {"ok": False, "status": 7, "error": "openSession failed"}
            elif req["password"] == "die":
                sys.stderr.write("simulated crash\\n"); sys.stderr.flush(); sys.exit(3)
            else:
                session = True; out = {"ok": True}
        elif cmd == "invoke":
            if not session:
                out = {"ok": False, "status": 4, "error": "not logged in"}
            elif "datapointReadListValue" in req["url"]:
                out = {"ok": True, "status": 0, "json": json.dumps({"response": {"data": [{"value": 1234}]}})}
            elif "setpointWriteValue" in req["url"]:
                out = {"ok": True, "status": 26, "json": json.dumps({"error": {"body": "device said no"}})}
            else:
                out = {"ok": True, "status": 0, "json": json.dumps({"url": req["url"]})}
        elif cmd == "close":
            session = False; out = {"ok": True}
        elif cmd == "version":
            out = {"ok": True, "version": "test"}
        else:
            out = {"ok": False, "status": -1, "error": "unknown"}
        print(json.dumps(out), flush=True)
    '''
)


@pytest.fixture
def client(tmp_path):
    script = tmp_path / "fake_helper.py"
    script.write_text(FAKE_HELPER)
    c = HelperClient(str(tmp_path / "data"), argv=[sys.executable, str(script)], lib_path="/not/used")
    yield c
    c.close()


def test_login_and_invoke(client) -> None:
    client.login(" abc123 ", "pw")
    out = client.invoke("setpointReadListValue", {"list": [{"obj": 0, "address": 16}]})
    assert out["url"].startswith("nabto://abc123.remote.lscontrol.dk/setpointReadListValue.json?json=")
    assert json.loads(out["url"].split("json=", 1)[1]) == {"request": {"list": [{"obj": 0, "address": 16}]}}
    assert client.invoke("datapointReadListValue", {"list": []}) == {"response": {"data": [{"value": 1234}]}}


def test_errors_are_reported(client) -> None:
    with pytest.raises(NabtoError) as err:
        client.login("abc123", "bad")
    assert err.value.status == 7  # shown to the person as a wrong login
    client.login("abc123", "pw")
    with pytest.raises(NabtoError, match="device said no"):  # error JSON from the unit
        client.invoke("setpointWriteValue", {"list": []})


def test_not_logged_in(client) -> None:
    with pytest.raises(NabtoError) as err:
        client.invoke("datapointReadListValue", {"list": []})
    assert err.value.status == 4


def test_helper_crash_shows_its_message_and_recovers(client) -> None:
    with pytest.raises(NabtoError, match="simulated crash"):
        client.login("abc123", "die")
    client.login("abc123", "pw")  # a new helper process is started
    assert client.invoke("datapointReadListValue", {"list": []})["response"]["data"][0]["value"] == 1234


def test_missing_helper_program(tmp_path) -> None:
    c = HelperClient(str(tmp_path), argv=[str(tmp_path / "nope")], lib_path="/not/used")
    with pytest.raises(NabtoError, match="startet|starten"):
        c.login("abc123", "pw")


def _fake_deb(files: dict[str, bytes], links: dict[str, str] | None = None) -> bytes:
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tf:
        for name, data in files.items():
            info = tarfile.TarInfo("./" + name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        for name, target in (links or {}).items():
            info = tarfile.TarInfo("./" + name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            tf.addfile(info)
    data = lzma.compress(tar_buf.getvalue())

    def member(name: str, body: bytes) -> bytes:
        hdr = f"{name + '/':<16}{0:<12}{0:<6}{0:<6}{100644:<8}{len(body):<10}`\n".encode()
        return hdr + body + (b"\n" if len(body) % 2 else b"")

    return b"!<arch>\n" + member("debian-binary", b"2.0\n") + member("data.tar.xz", data)


def test_extract_deb_with_links(tmp_path) -> None:
    deb = _fake_deb({"lib/x86_64-linux-gnu/libc-2.36.so": b"REAL"}, {"lib/x86_64-linux-gnu/libc.so.6": "libc-2.36.so"})
    nabto.extract_deb(deb, {"lib/x86_64-linux-gnu/libc.so.6": "libc.so.6"}, str(tmp_path))
    assert (tmp_path / "libc.so.6").read_bytes() == b"REAL"
    with pytest.raises(NabtoError):
        nabto.extract_deb(deb, {"lib/missing.so": "x"}, str(tmp_path))


def test_runtime_download_checks_and_unpacks(tmp_path, monkeypatch) -> None:
    """ensure_runtime fetches the three Debian packages; a wrong checksum is refused."""
    import hashlib

    debs = {}
    packages = []
    for pool_dir, name, pinned, _sha, pattern, wanted in nabto.RUNTIME_PACKAGES:
        deb = _fake_deb({src: f"{dst}-content".encode() for src, dst in wanted.items()})
        debs[nabto.DEBIAN_POOL + pool_dir + pinned] = deb
        packages.append((pool_dir, name, pinned, hashlib.sha256(deb).hexdigest(), pattern, wanted))
    monkeypatch.setattr(nabto, "RUNTIME_PACKAGES", packages)
    monkeypatch.setattr(nabto, "_download", lambda url: debs[url])
    out = nabto.ensure_runtime(str(tmp_path / "rt"))
    assert (tmp_path / "rt" / "ld-linux-x86-64.so.2").read_bytes() == b"ld-linux-x86-64.so.2-content"
    assert os.path.exists(os.path.join(out, ".complete"))
    # a damaged download is refused
    bad = list(packages)
    bad[0] = (*bad[0][:3], "0" * 64, *bad[0][4:])
    monkeypatch.setattr(nabto, "RUNTIME_PACKAGES", bad)
    with pytest.raises(NabtoError, match="Prüfsumme"):
        nabto.ensure_runtime(str(tmp_path / "rt2"))


def test_loader_gets_the_executable_permission(tmp_path, monkeypatch) -> None:
    """The glibc loader is started like a program; files saved without the permission (older downloads) are repaired."""
    import hashlib
    import stat

    packages = []
    debs = {}
    for pool_dir, name, pinned, _sha, pattern, wanted in nabto.RUNTIME_PACKAGES:
        deb = _fake_deb({src: b"x" for src in wanted})
        debs[nabto.DEBIAN_POOL + pool_dir + pinned] = deb
        packages.append((pool_dir, name, pinned, hashlib.sha256(deb).hexdigest(), pattern, wanted))
    monkeypatch.setattr(nabto, "RUNTIME_PACKAGES", packages)
    monkeypatch.setattr(nabto, "_download", lambda url: debs[url])
    rt = nabto.ensure_runtime(str(tmp_path / "rt"))
    ld = os.path.join(rt, nabto.LOADER)
    assert os.stat(ld).st_mode & stat.S_IXUSR
    os.chmod(ld, 0o644)  # as written by the older version
    nabto.ensure_runtime(rt)
    assert os.stat(ld).st_mode & stat.S_IXUSR


def test_blocked_config_folder_falls_back_to_another_folder(tmp_path, monkeypatch) -> None:
    """If programs can't be started from the config folder, everything is copied to a temporary folder."""
    rt = tmp_path / "config" / "runtime"
    rt.mkdir(parents=True)
    helper_script = tmp_path / "config" / "helper"
    script = tmp_path / "fake_helper.py"
    script.write_text(FAKE_HELPER)
    helper_script.write_text(FAKE_HELPER)
    loader = rt / nabto.LOADER
    # a "loader" that starts the fake helper, but is not executable (as on a locked-down folder)
    loader.write_text(f"#!{sys.executable}\nimport os, sys\nos.execv(sys.executable, [sys.executable, sys.argv[-1]])\n")
    os.chmod(loader, 0o644)
    lib = tmp_path / "config" / "lib.so"
    lib.write_bytes(b"lib")
    monkeypatch.setattr(nabto, "ensure_runtime", lambda d: str(rt))
    monkeypatch.setattr(nabto, "helper_path", lambda: str(helper_script))
    monkeypatch.setattr(nabto, "make_executable", lambda p: None if str(p).startswith(str(tmp_path / "config")) else os.chmod(p, 0o755))
    monkeypatch.setattr(tempfile_module(), "gettempdir", lambda: str(tmp_path / "tmpdir"))
    (tmp_path / "tmpdir").mkdir()
    c = HelperClient(str(tmp_path / "data"), lib_path=str(lib))
    try:
        c.login("abc123", "pw")  # first start fails with "Permission denied", then the copy in the other folder is used
        assert c._relocated and str(tmp_path / "tmpdir") in c._argv[0]
        assert c.invoke("datapointReadListValue", {"list": []})["response"]["data"][0]["value"] == 1234
    finally:
        c.close()


def tempfile_module():
    import tempfile

    return tempfile


def test_client_choice(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(nabto, "ensure_library", lambda d: "/lib/x.so")
    monkeypatch.setattr(nabto, "platform_key", lambda: ("linux", "x86_64"))
    monkeypatch.setattr(nabto, "is_musl", lambda: True)
    monkeypatch.setattr(nabto, "ensure_runtime", lambda d: d)
    assert isinstance(nabto.create_client(str(tmp_path)), HelperClient)


def test_hot_water_temperature_decoding() -> None:
    from custom_components.proxon_control import registers as R

    assert R.decode("water", 1360) == 36.0  # (raw - 1000) / 10
    assert R.decode("water", 485) == 48.5  # plain tenths
    assert R.decode("water", 0) is None
    assert R.decode("t300", 949) == -5.1
    reg = R.BY_KEY["WarmwasserIstTemperatur"]
    assert (reg.set_point, reg.read) == (False, (3, 14))


def test_log_errors_explains_unspecified_failures(tmp_path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "nabto-api-log.txt").write_text(
        "x [____CRYPTO,info_] a.cpp(1):   fine\n"
        "x [____CRYPTO,warn_] certificatestore.cpp(144):           No root certificates inserted in root store, looked in /a\n"
        "x [___DEFAULT,error] peerapplication.cpp(46):             clientpeer-1: The certificate cannot be verified against the root certificate\n"
        "x [_______APP,error] nabto_session.cpp(66):               static resource dir not found (x)\n"
        "x [_______APP,error] nabto_client_facade.cpp(733):        Login failed, errorCode: 1000012\n"
    )
    out = nabto.log_errors(str(tmp_path))
    assert "Login failed" in out and "cannot be verified" in out and "static resource" not in out
    assert nabto.log_errors(str(tmp_path / "nowhere")) == ""
