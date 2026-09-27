"""Sensors — last call, call log, and per-direction counts."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            LastCallSensor(coordinator, entry),
            CallLogSensor(coordinator, entry),
            CountSensor(coordinator, entry, "count_today", "Calls Today", "mdi:phone-log"),
            CountSensor(coordinator, entry, "count_missed", "Missed Calls", "mdi:phone-missed"),
        ]
    )


class _Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Landline (Livebox)",
            manufacturer="Orange",
            model="Livebox",
        )


class LastCallSensor(_Base):
    _attr_icon = "mdi:phone-log"
    _attr_name = "Last Call"

    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_last_call"

    @property
    def native_value(self):
        last = (self.coordinator.data or {}).get("last")
        return last["display"] if last else "None"

    @property
    def extra_state_attributes(self):
        return (self.coordinator.data or {}).get("last") or {}


class CallLogSensor(_Base):
    _attr_icon = "mdi:phone-log-outline"
    _attr_name = "Call Log"
    _attr_native_unit_of_measurement = "calls"

    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_call_log"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("count_today", 0)

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data or {}
        return {
            "calls": d.get("calls", []),
            "count_today": d.get("count_today", 0),
            "count_missed": d.get("count_missed", 0),
            "count_incoming": d.get("count_incoming", 0),
            "count_outgoing": d.get("count_outgoing", 0),
            "ringing": d.get("ringing", False),
            "contacts": d.get("contacts", []),
        }


class CountSensor(_Base):
    def __init__(self, coordinator, entry, key, name, icon):
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon

    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_{self._key}"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(self._key, 0)
