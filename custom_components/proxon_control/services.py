"""Actions for the weekly ventilation schedule: set one phase, copy one day to other days."""
from __future__ import annotations

from datetime import time

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import ProxonCoordinator
from .dashboard import build
from .schedule import DAYS, ScheduleError, plan_day, read_day, set_phase, unit_clock

ATTR_CONFIG_ENTRY = "config_entry_id"
SERVICE_SET_PHASE = "set_schedule_phase"
SERVICE_COPY_DAY = "copy_schedule_day"
SERVICE_DASHBOARD = "create_dashboard"
DASHBOARD_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY): cv.string})

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


def _day_name(hass: HomeAssistant, day: int) -> str:
    lang = "de" if (hass.config.language or "").startswith("de") else "en"
    return DAY_NAMES[lang][day]


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
        translation_domain=DOMAIN, translation_key=err.key, translation_placeholders={"day": _day_name(hass, day), **err.placeholders}
    )


def _phases(hass: HomeAssistant, coordinator: ProxonCoordinator, day: int):
    phases = read_day(coordinator.data or {}, day)
    if phases is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="schedule_not_loaded")
    return phases


async def _write(coordinator: ProxonCoordinator, writes: list[tuple[str, int]]) -> None:
    for key, value in writes:
        await coordinator.async_write(key, value)


def async_setup_services(hass: HomeAssistant) -> None:
    async def set_schedule_phase(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY))
        day = DAYS.index(call.data["day"])
        old = _phases(hass, coordinator, day)
        new = set_phase(old, call.data["phase"] - 1, _minutes(call.data.get("start")), _minutes(call.data.get("end")), call.data["level"])
        try:
            writes = plan_day(day, old, new, unit_clock(coordinator.data or {}))
        except ScheduleError as err:
            raise _fail(hass, day, err) from err
        await _write(coordinator, writes)

    async def copy_schedule_day(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY))
        source = DAYS.index(call.data["source_day"])
        phases = _phases(hass, coordinator, source)
        now = unit_clock(coordinator.data or {})
        # check every day first: nothing is written unless all target days can take the copy
        plans: list[list[tuple[str, int]]] = []
        for name in dict.fromkeys(call.data["target_days"]):
            day = DAYS.index(name)
            if day == source:
                continue
            try:
                plans.append(plan_day(day, _phases(hass, coordinator, day), phases, now))
            except ScheduleError as err:
                raise _fail(hass, day, err) from err
        for writes in plans:
            await _write(coordinator, writes)

    async def create_dashboard(call: ServiceCall) -> ServiceResponse:
        """The ready-made dashboard, with this unit's real entity IDs. Returned as the dashboard itself (starting with
        `views:`), so the whole answer shown under Developer tools can be pasted into the raw configuration editor."""
        return build(hass, _entry(hass, call.data.get(ATTR_CONFIG_ENTRY)))

    hass.services.async_register(
        DOMAIN, SERVICE_DASHBOARD, create_dashboard, schema=DASHBOARD_SCHEMA, supports_response=SupportsResponse.ONLY
    )
    hass.services.async_register(DOMAIN, SERVICE_SET_PHASE, set_schedule_phase, schema=SET_PHASE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_COPY_DAY, copy_schedule_day, schema=COPY_DAY_SCHEMA)
