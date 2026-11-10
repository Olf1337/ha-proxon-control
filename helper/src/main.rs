//! Small helper process for the Proxon Control Home Assistant integration.
//!
//! Home Assistant OS runs Python on Alpine Linux (musl), which can't load Nabto's glibc-only client library.
//! The integration starts this program through a glibc loader it downloads, and talks to it with one JSON
//! object per line:
//!   {"cmd":"login","lib":"/path/libnabto_client_api.so","home":"/path/home","user":"…","password":"…","interface":"<xml>"}
//!   {"cmd":"invoke","url":"nabto://…"}
//!   {"cmd":"check","lib":"…","home":"…","interface":"<xml>"}   (loads the library and the interface without logging in)
//! Every request gets one reply line: {"ok":true,…} or {"ok":false,"status":N,"error":"…"}.

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::io::{BufRead, Write};

use serde_json::{json, Value};

type Handle = *mut c_void;
const OK: c_int = 0;
const FAILED_WITH_JSON: c_int = 26;

struct Lib {
    _lib: libloading::Library,
    startup: unsafe extern "C" fn(*const c_char) -> c_int,
    set_option: unsafe extern "C" fn(*const c_char, *const c_char) -> c_int,
    open_session: unsafe extern "C" fn(*mut Handle, *const c_char, *const c_char) -> c_int,
    open_bare: unsafe extern "C" fn(*mut Handle) -> c_int,
    install_resources: unsafe extern "C" fn(*const c_char) -> c_int,
    create_profile: unsafe extern "C" fn(*const c_char, *const c_char) -> c_int,
    set_interface: unsafe extern "C" fn(Handle, *const c_char, *mut *mut c_char) -> c_int,
    rpc_invoke: unsafe extern "C" fn(Handle, *const c_char, *mut *mut c_char) -> c_int,
    free: unsafe extern "C" fn(*mut c_void) -> c_int,
    close_session: unsafe extern "C" fn(Handle) -> c_int,
}

fn load(path: &str) -> Result<Lib, String> {
    // SAFETY: the vendor's client library; symbols follow its published C interface.
    unsafe {
        let lib = libloading::Library::new(path).map_err(|e| format!("cannot load {path}: {e}"))?;
        macro_rules! sym {
            ($n:literal) => {
                *lib.get(concat!($n, "\0").as_bytes()).map_err(|e| format!("{}: {e}", $n))?
            };
        }
        Ok(Lib {
            startup: sym!("nabtoStartup"),
            set_option: sym!("nabtoSetOption"),
            open_session: sym!("nabtoOpenSession"),
            open_bare: sym!("nabtoOpenSessionBare"),
            install_resources: sym!("nabtoInstallDefaultStaticResources"),
            create_profile: sym!("nabtoCreateProfile"),
            set_interface: sym!("nabtoRpcSetDefaultInterface"),
            rpc_invoke: sym!("nabtoRpcInvoke"),
            free: sym!("nabtoFree"),
            close_session: sym!("nabtoCloseSession"),
            _lib: lib,
        })
    }
}

struct State {
    lib: Option<Lib>,
    session: Handle,
}

fn c(s: &str) -> Result<CString, String> {
    CString::new(s).map_err(|e| e.to_string())
}

fn err(status: c_int, msg: impl Into<String>) -> Value {
    json!({"ok": false, "status": status, "error": msg.into()})
}

impl State {
    fn take(&self, p: *mut c_char) -> String {
        if p.is_null() {
            return String::new();
        }
        let lib = self.lib.as_ref().unwrap();
        // SAFETY: NUL-terminated buffer from the library, released with nabtoFree.
        unsafe {
            let s = CStr::from_ptr(p).to_string_lossy().into_owned();
            (lib.free)(p as *mut c_void);
            s
        }
    }

    fn start(&mut self, req: &Value) -> Result<(), Value> {
        if self.lib.is_some() {
            return Ok(());
        }
        let path = req["lib"].as_str().unwrap_or_default();
        let lib = load(path).map_err(|e| err(-1, e))?;
        let home = c(req["home"].as_str().unwrap_or_default()).map_err(|e| err(-1, e))?;
        let _ = std::fs::create_dir_all(req["home"].as_str().unwrap_or("."));
        // SAFETY: valid NUL-terminated strings.
        unsafe {
            let st = (lib.startup)(home.as_ptr());
            if st != OK {
                return Err(err(st, "nabtoStartup failed"));
            }
            // like the original app: install Nabto's root certificates, otherwise the signed login certificate
            // can't be verified and openSession fails with "unspecified error" (18)
            let st = (lib.install_resources)(std::ptr::null());
            if st != OK {
                return Err(err(st, "nabtoInstallDefaultStaticResources failed"));
            }
            let (k, v) = (c("urlPortalHostName").unwrap(), c("lscontrol").unwrap());
            (lib.set_option)(k.as_ptr(), v.as_ptr());
        }
        self.lib = Some(lib);
        Ok(())
    }

    fn set_interface(&mut self, xml: &str) -> Result<(), Value> {
        let lib = self.lib.as_ref().unwrap();
        let x = c(xml).map_err(|e| err(-1, e))?;
        let mut e: *mut c_char = std::ptr::null_mut();
        // SAFETY: valid session and string.
        let st = unsafe { (lib.set_interface)(self.session, x.as_ptr(), &mut e) };
        let msg = self.take(e);
        if st != OK {
            return Err(err(st, format!("interface rejected: {msg}")));
        }
        Ok(())
    }

    fn close(&mut self) {
        if let Some(lib) = &self.lib {
            if !self.session.is_null() {
                // SAFETY: closing our own session.
                unsafe { (lib.close_session)(self.session) };
                self.session = std::ptr::null_mut();
            }
        }
    }

    fn handle(&mut self, req: &Value) -> Value {
        match req["cmd"].as_str().unwrap_or_default() {
            "check" => {
                if let Err(e) = self.start(req) {
                    return e;
                }
                self.close();
                let lib = self.lib.as_ref().unwrap();
                // SAFETY: out-pointer we own.
                let st = unsafe { (lib.open_bare)(&mut self.session) };
                if st != OK {
                    return err(st, "bare session failed");
                }
                if let Err(e) = self.set_interface(req["interface"].as_str().unwrap_or_default()) {
                    return e;
                }
                self.close();
                json!({"ok": true})
            }
            "login" => {
                if let Err(e) = self.start(req) {
                    return e;
                }
                self.close();
                let (user, pw) = match (c(req["user"].as_str().unwrap_or_default()), c(req["password"].as_str().unwrap_or_default())) {
                    (Ok(u), Ok(p)) => (u, p),
                    _ => return err(-1, "invalid user or password text"),
                };
                let lib = self.lib.as_ref().unwrap();
                // SAFETY: valid strings and an out-pointer we own.
                let st = unsafe {
                    let mut st = (lib.open_session)(&mut self.session, user.as_ptr(), pw.as_ptr());
                    if st != OK {
                        // like the original app: create the portal profile, then open again
                        let created = (lib.create_profile)(user.as_ptr(), pw.as_ptr());
                        if created != OK {
                            return err(created, "createProfile failed");
                        }
                        st = (lib.open_session)(&mut self.session, user.as_ptr(), pw.as_ptr());
                    }
                    st
                };
                if st != OK {
                    self.session = std::ptr::null_mut();
                    return err(st, "openSession failed");
                }
                if let Err(e) = self.set_interface(req["interface"].as_str().unwrap_or_default()) {
                    return e;
                }
                json!({"ok": true})
            }
            "invoke" => {
                let Some(lib) = self.lib.as_ref() else { return err(3, "not started") };
                if self.session.is_null() {
                    return err(4, "not logged in");
                }
                let url = match c(req["url"].as_str().unwrap_or_default()) {
                    Ok(u) => u,
                    Err(e) => return err(-1, e),
                };
                let mut out: *mut c_char = std::ptr::null_mut();
                // SAFETY: valid session and URL; reply released in take().
                let st = unsafe { (lib.rpc_invoke)(self.session, url.as_ptr(), &mut out) };
                let text = self.take(out);
                if st != OK && st != FAILED_WITH_JSON {
                    return err(st, "rpcInvoke failed");
                }
                json!({"ok": true, "status": st, "json": text})
            }
            "close" => {
                self.close();
                json!({"ok": true})
            }
            "version" => json!({"ok": true, "version": env!("CARGO_PKG_VERSION")}),
            other => err(-1, format!("unknown command {other}")),
        }
    }
}

fn main() {
    let mut state = State { lib: None, session: std::ptr::null_mut() };
    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        if line.trim().is_empty() {
            continue;
        }
        let reply = match serde_json::from_str::<Value>(&line) {
            Ok(req) => state.handle(&req),
            Err(e) => err(-1, format!("bad request: {e}")),
        };
        if writeln!(stdout, "{reply}").and_then(|_| stdout.flush()).is_err() {
            break;
        }
    }
    state.close();
}
