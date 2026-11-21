# Quality scale: self-assessment

How Proxon Control stands against Home Assistant's [Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
(made for integrations in Home Assistant itself; a custom integration can use it as a checklist). Checked for 1.0.

**Bronze: met. Silver: met except test coverage (94 %, Silver asks for more than 95 %). Gold: mostly met, see the open points.**

## Bronze

| Rule | | How |
|---|---|---|
| Config flow | ✅ | set up in the user interface, with Device ID and password or through the bridge |
| Config flow test coverage | ✅ | `tests/test_integration.py`, `test_local.py`, `test_readback_and_bridge.py` (config_flow.py 96 %) |
| Test before configure | ✅ | the dialog tests the connection before saving |
| Test before setup | ✅ | the first read fails the setup (retried by Home Assistant) |
| Unique config entry | ✅ | one unit per Home Assistant (`single_config_entry`), unique ID = Device ID |
| Runtime data | ✅ | `entry.runtime_data` holds the coordinator |
| Entity unique ID / has entity name | ✅ | `{device id}_{key}`, names from translations |
| Entity event setup | ✅ | listeners added in `async_added_to_hass`, removed on unload |
| Appropriate polling | ✅ | 10 s by default, adjustable 5–3600 s |
| Action setup | ✅ | actions registered in `async_setup`, they check the entry when called |
| Common modules | ✅ | coordinator, entity base class, API in their own modules |
| Dependency transparency | ✅ | no Python requirements; Nabto's library is fetched from Nabto's own release (see README) |
| Brands | ✅ | `brand/` in the integration |
| Docs: description, installation, actions, removal | ✅ | README |

## Silver

| Rule | | How |
|---|---|---|
| Action exceptions | ✅ | refused actions raise translated `ServiceValidationError` / `HomeAssistantError` |
| Config entry unloading | ✅ | platforms, page, timers and notices go with the entry |
| Entity unavailable / log when unavailable | ✅ | coordinator: entities unavailable while the unit doesn't answer, logged once and on recovery |
| Parallel updates | ✅ | `PARALLEL_UPDATES = 1` for platforms that write (the unit allows only a few sessions), `0` for read-only ones |
| Reauthentication flow | ✅ | a refused password asks for the new one |
| Integration owner | ✅ | `codeowners` in the manifest |
| Docs: configuration and installation parameters | ✅ | README, options described in the dialogs |
| Test coverage above 95 % | ⏳ | 94 % (`pytest --cov`); missing are mostly error paths of the Nabto helper |

## Gold

| Rule | | How |
|---|---|---|
| Devices | ✅ | the unit, every room and the weekly schedule days as devices |
| Diagnostics | ✅ | download without IP address, password or photo |
| Entity category, device class, disabled by default | ✅ | diagnostic values as diagnostic, rarely used ones disabled |
| Entity and exception translations | ✅ | German and English |
| Repair issues | ✅ | filter change, unit fault, clock off, compressor cycling, legionella risk, deprecated dashboard |
| Docs: data update, examples, known limits, supported devices and functions, troubleshooting, use cases | ✅ | README, blueprints |
| Stale devices | ✅ | a room the unit no longer reports can be deleted on its device page; the unit and current rooms can't |
| Discovery / discovery update info | ➖ | the unit has no DHCP or zeroconf signature; the setup searches the home network itself |
| Dynamic devices | ⏳ | rooms are created at start; a room connected later appears after a restart |
| Icon translations | ⏳ | icons are set in code, not in `icons.json` |
| Reconfiguration flow | ⏳ | connection details are changed in the options; no separate *Reconfigure* step yet |

## Platinum

| Rule | | How |
|---|---|---|
| Async dependency | ➖ | the unit's protocols are synchronous (UDP, Nabto's C library); they run in the executor |
| Inject web session | ➖ | no HTTP client of Home Assistant's kind is used for the unit |
| Strict typing | ⏳ | mypy runs on every change, not yet in strict mode |

✅ met · ⏳ open · ➖ does not apply
