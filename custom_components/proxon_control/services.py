"""Actions: set one phase of the weekly ventilation schedule, copy one day to other days, create the ready-made dashboard
(put into Home Assistant, or returned to paste), install its glass theme."""
from __future__ import annotations

from datetime import time

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import CONF_PICTURE_THEME, DOMAIN
from .coordinator import ProxonCoordinator
from .dashboard import build
from .dashboard_store import DashboardStoreError, async_store_dashboard
from .entity import schedule_device
from .schedule import DAYS, ScheduleError, plan_day, read_day, set_phase, unit_clock
from .theme import THEME_FILE, THEME_NAME, async_install_theme

ATTR_CONFIG_ENTRY = "config_entry_id"
SERVICE_SET_PHASE = "set_schedule_phase"
SERVICE_COPY_DAY = "copy_schedule_day"
SERVICE_DASHBOARD = "create_dashboard"
SERVICE_THEME = "install_glass_theme"
DASHBOARD_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY): cv.string})
ATTR_PASTE_ONLY = "paste_only"
CREATE_DASHBOARD_SCHEMA = DASHBOARD_SCHEMA.extend({vol.Optional(ATTR_PASTE_ONLY, default=False): cv.boolean})
DASHBOARD_URL = "proxon-dashboard"

DAY_NAMES = {
    "de": ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}

SET_PHASE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Required("day"): vol.In(DAYS),
        vol.Required("phase"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3)),
        vol.Optional("start"): cv.time,
        vol.Optional("end"): cv.time,
        vol.Required("level"): vol.All(vol.Coerce(int), vol.Range(min=0, max=4)),
    }
)
COPY_DAY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Required("source_day"): vol.In(DAYS),
        vol.Required("target_days"): vol.All(cv.ensure_list, [vol.In(DAYS)], vol.Length(min=1)),
    }
)


def _minutes(value: time | None) -> int | None:
    return None if value is None else value.hour * 60 + value.minute


def day_name(hass: HomeAssistant, day: int) -> str:
    lang = "de" if (hass.config.language or "").startswith("de") else "en"
    return DAY_NAMES[lang][day]


def schedule_day_device(hass: HomeAssistant, coordinator: ProxonCoordinator, day: int):
    """The device of one weekday of the ventilation schedule ("Proxon Zeitprogramm Montag")."""
    german = (hass.config.language or "").startswith("de")
    return schedule_device(coordinator, day, day_name(hass, day), "Zeitprogramm" if german else "schedule")


def _entry(hass: HomeAssistant, entry_id: str | None):
    loaded = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
    if entry_id:
        loaded = [e for e in loaded if e.entry_id == entry_id]
    if len(loaded) != 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="schedule_no_entry")
    return loaded[0]


def _coordinator(hass: HomeAssistant, entry_id: str | None) -> ProxonCoordinator:
    return _entry(hass, entry_id).runtime_data


def _fail(hass: HomeAssistant, day: int, err: ScheduleError) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN, translation_key=err.key, translation_placeholders={"day": day_name(hass, day), **err.placeholders}
    )


def _phases(hass: HomeAssistant, coordinator: ProxonCoordinator, day: int):
    phases = read_day(coordinator.data or {}, day)
    if phases is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="schedule_not_loaded")
    return phases


async def _write(coordinator: ProxonCoordinator, writes: list[tuple[str, int]]) -> None:
    for key, value in writes:
        await coordinator.async_write(key, value)


async def async_set_phase(
    hass: HomeAssistant, coordinator: ProxonCoordinator, day: int, phase: int, start: int | None, end: int | None, level: int | None,
) -> None:
    """Change one phase (0-2) of a day: start/end in minutes after midnight, None = keep; level None = keep. Checked against
    the unit's rules first (a translated error says why a change isn't possible)."""
    old = _phases(hass, coordinator, day)
    new = set_phase(old, phase, start, end, old[phase].level if level is None else level)
    try:
        writes = plan_day(day, old, new, unit_clock(coordinator.data or {}))
    except ScheduleError as err:
        raise _fail(hass, day, err) from err
    await _write(coordinator, writes)


async def async_copy_day(hass: HomeAssistant, coordinator: ProxonCoordinator, source: int, targets: list[int]) -> None:
    """Copy one day's phases to other days. Every day is checked first: nothing is written unless all can take the copy."""
    phases = _phases(hass, coordinator, source)
    now = unit_clock(coordinator.data or {})
    plans: list[list[tuple[str, int]]] = []
    for day in dict.fromkeys(targets):
        if day == source:
            continue
        try:
            # phases across midnight come from a day the unit already holds: they may be copied
            plans.append(plan_day(day, _phases(hass, coordinator, day), phases, now, allow_overnight=True))
        except ScheduleError as err:
            raise _fail(hass, day, err) from err
    for writes in plans:
        await _write(coordinator, writes)


def async_setup_services(hass: HomeAssistant) -> None:
    async def set_schedule_phase(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY))
        await async_set_phase(
            hass, coordinator, DAYS.index(call.data["day"]), call.data["phase"] - 1,
            _minutes(call.data.get("start")), _minutes(call.data.get("end")), call.data["level"],
        )

    async def copy_schedule_day(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY))
        await async_copy_day(hass, coordinator, DAYS.index(call.data["source_day"]), [DAYS.index(d) for d in call.data["target_days"]])

    async def create_dashboard(call: ServiceCall) -> ServiceResponse:
        """The ready-made dashboard, with this unit's real entity IDs: put into Home Assistant as the dashboard "Proxon"
        (created on the first run, written anew on every further one). With "paste only" it is just returned (starting
        with `views:`), to paste into the raw configuration editor of a dashboard of one's own."""
        entry = _entry(hass, call.data.get(ATTR_CONFIG_ENTRY))
        config = build(hass, entry)
        if call.data.get(ATTR_PASTE_ONLY):
            return config
        german = (hass.config.language or "").startswith("de")
        # a second unit gets a dashboard of its own
        others = [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]
        first = not others or entry.entry_id == sorted(e.entry_id for e in hass.config_entries.async_entries(DOMAIN))[0]
        url = DASHBOARD_URL if first else f"{DASHBOARD_URL}-{entry.entry_id[-6:].lower()}"
        try:
            created = await async_store_dashboard(hass, url, "Proxon" if first else f"Proxon {entry.title}", config)
        except DashboardStoreError as err:
            if str(err) == "yaml":
                reason = (f"Unter /{url} gibt es schon ein Dashboard aus der YAML-Konfiguration; das wird nicht überschrieben."
                          if german else f"There is a dashboard from the YAML configuration at /{url}; it isn't written over.")
            else:
                reason = ("Diese Home-Assistant-Version lässt das Anlegen von Dashboards nicht zu."
                          if german else "This version of Home Assistant doesn't let the dashboard be created.")
            hint = (" Führe die Aktion mit „Nur zum Einfügen“ aus und füge die Antwort im Raw-Konfigurationseditor eines "
                    "eigenen Dashboards ein." if german else
                    " Run the action with \"paste only\" and paste the answer into the raw configuration editor of a dashboard.")
            raise ServiceValidationError(reason + hint) from err
        if german:
            message = (f"Das Dashboard „Proxon“ ist angelegt: Seitenleiste oder /{url}." if created else
                       f"Das Dashboard unter /{url} ist neu geschrieben. Änderungen, die dort von Hand gemacht wurden, sind ersetzt.")
        else:
            message = (f"The dashboard \"Proxon\" is created: sidebar or /{url}." if created else
                       f"The dashboard at /{url} is written anew. Changes made there by hand are replaced.")
        return {"url": f"/{url}", "created": created, "message": message}

    async def install_glass_theme(call: ServiceCall) -> ServiceResponse:
        """Write the glass theme into the themes folder, reload the themes, and draw the dashboard pictures dark (they sit
        on dark glass). Tells whether Home Assistant loads the theme, and what to add to configuration.yaml if not."""
        entry_id = call.data.get(ATTR_CONFIG_ENTRY)
        entries = [_entry(hass, entry_id)] if entry_id else [
            e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED
        ]
        installed = await async_install_theme(hass)
        for entry in entries:
            if entry.options.get(CONF_PICTURE_THEME) != "dark":
                hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_PICTURE_THEME: "dark"})
        german = (hass.config.language or "").startswith("de")
        if installed:
            message = (f"Das Theme „{THEME_NAME}“ ist installiert, die Dashboard-Bilder sind auf dunkel gestellt. Das Dashboard "
                       "nutzt es auf allen Reitern; für ein Wandtablet kannst du es im Profil auch für das ganze Gerät wählen."
                       if german else
                       f"The theme \"{THEME_NAME}\" is installed and the dashboard pictures are set to dark. The dashboard uses it on "
                       "all tabs; on a wall tablet you can also choose it for the whole device in the profile.")
        else:
            message = (f"Die Datei themes/{THEME_FILE} ist geschrieben, aber Home Assistant lädt den Ordner themes nicht. Ergänze in "
                       "configuration.yaml unter frontend: die Zeile „themes: !include_dir_merge_named themes“, starte Home "
                       "Assistant neu und führe die Aktion noch einmal aus."
                       if german else
                       f"The file themes/{THEME_FILE} is written, but Home Assistant doesn't load the themes folder. Add the line "
                       "\"themes: !include_dir_merge_named themes\" under frontend: in configuration.yaml, restart Home Assistant "
                       "and run the action again.")
        return {"theme": THEME_NAME, "installed": installed, "file": f"themes/{THEME_FILE}", "message": message}

    hass.services.async_register(
        DOMAIN, SERVICE_DASHBOARD, create_dashboard, schema=CREATE_DASHBOARD_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN, SERVICE_THEME, install_glass_theme, schema=DASHBOARD_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(DOMAIN, SERVICE_SET_PHASE, set_schedule_phase, schema=SET_PHASE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_COPY_DAY, copy_schedule_day, schema=COPY_DAY_SCHEMA)
