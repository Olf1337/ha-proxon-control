# Quality scale: self-assessment

How Proxon Control stands against Home Assistant's [Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
(made for integrations in Home Assistant itself; a custom integration can use it as a checklist). Checked for 1.0.

**Bronze, Silver and Gold: met** (Gold since 1.1; discovery does not apply to this unit).

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
| Test coverage above 95 % | ✅ | 96 %; the tests on GitHub fail below 95 % (`--cov-fail-under=95`) |

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
| Dynamic devices | ✅ | a room connected later gets its entities at the next reading (`entity.watch_new_rooms`) and goes into its area |
| Icon translations | ✅ | every icon in `icons.json` (state icons for the heating element); `tests/test_icons.py` keeps icons out of the code |
| Reconfiguration flow | ✅ | *Reconfigure*: password, connection and address (bridge: address, port, key), tested before saving |

## Platinum

| Rule | | How |
|---|---|---|
| Async dependency | ➖ | the unit's protocols are synchronous (UDP, Nabto's C library); they run in the executor |
| Inject web session | ➖ | no HTTP client of Home Assistant's kind is used for the unit |
| Strict typing | ⏳ | mypy runs on every change, not yet in strict mode |

✅ met · ⏳ open · ➖ does not apply
