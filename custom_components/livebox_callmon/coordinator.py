"""DataUpdateCoordinator — polls the call list, detects live rings, enriches
each call with contact name + tag, and fires HA events.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import timedelta

from .const import (
    DIRECTION_INCOMING,
    DIRECTION_MISSED,
    DIRECTION_OUTGOING,
    EVENT_NEW_CALL,
    EVENT_RING,
)
from .contacts import ContactStore
from .livebox import LiveboxClient, LiveboxError

_LOGGER = logging.getLogger(__name__)


def normalise_call(raw: dict) -> dict:
    """Map a Livebox call record to a stable, HA-friendly dict."""
    number = raw.get("remoteNumber") or raw.get("number") or "Unknown"
    name = raw.get("remoteName") or raw.get("name") or ""
    ctype = (raw.get("callType") or raw.get("type") or "").lower()
    origin = (raw.get("callOrigin") or "").lower()
    dest = (raw.get("callDestination") or "").lower()
    termination = (raw.get("terminationCause") or "").lower()

    if ctype == "missed" or termination == "unanswered":
        direction = DIRECTION_MISSED
    elif origin == "local":
        direction = DIRECTION_OUTGOING
    elif dest == "local" or origin in ("sip", "network"):
        direction = DIRECTION_INCOMING
    elif "out" in ctype:
        direction = DIRECTION_OUTGOING
    elif "in" in ctype:
        direction = DIRECTION_INCOMING
    else:
        direction = DIRECTION_INCOMING if ctype == "succeeded" else (ctype or "unknown")

    ts_raw = raw.get("startTime") or raw.get("time") or 0
    ts_iso = str(ts_raw)
    ts_disp = str(ts_raw)
    try:
        if isinstance(ts_raw, str) and "T" in ts_raw:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).astimezone()
            ts_iso = ts.isoformat()
            ts_disp = ts.strftime("%Y-%m-%d %H:%M")
        elif isinstance(ts_raw, (int, float)) or (isinstance(ts_raw, str) and ts_raw.isdigit()):
            ts = datetime.fromtimestamp(int(ts_raw), tz=timezone.utc).astimezone()
            ts_iso = ts.isoformat()
            ts_disp = ts.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        pass

    try:
        duration = int(raw.get("duration", 0))
    except (TypeError, ValueError):
        duration = 0

    box_id = raw.get("callId")
    call_id = f"lb-{box_id}" if box_id else hashlib.sha1(
        f"{number}|{ts_iso}|{direction}|{duration}".encode()
    ).hexdigest()[:16]

    return {
        "id": call_id,
        "number": number,
        "name": name,
        "display": name if name else number,
        "direction": direction,
        "timestamp": ts_iso,
        "time_display": ts_disp,
        "duration": duration,
    }


class LiveboxCoordinator(DataUpdateCoordinator):
    """Polls calls + live ring state, enriches with contacts."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: LiveboxClient,
        contacts: ContactStore,
        poll_interval: int,
        history_len: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="livebox_callmon",
            update_interval=timedelta(seconds=poll_interval),
        )
        self._client = client
        self._contacts = contacts
        self._history_len = history_len
        self._seen: set[str] = set()
        self._primed = False
        self._ringing = False
        self.history: list[dict] = []

    def _enrich(self, call: dict) -> dict:
        match = self._contacts.lookup(call["number"])
        if match:
            if match.get("name"):
                call["name"] = match["name"]
                call["display"] = match["name"]
            call["tag"] = match.get("tag", "other")
        else:
            call["tag"] = ""
        return call

    async def _async_update_data(self):
        try:
            raw_calls = await self._client.get_calls()
        except LiveboxError as err:
            raise UpdateFailed(str(err)) from err

        calls = [self._enrich(normalise_call(c)) for c in raw_calls]
        calls.sort(key=lambda c: c["timestamp"], reverse=True)

        new = [c for c in calls if c["id"] not in self._seen]
        for c in sorted(new, key=lambda c: c["timestamp"]):
            self._seen.add(c["id"])
            self.history.insert(0, c)
            if self._primed:
                self.hass.bus.async_fire(EVENT_NEW_CALL, c)
        self.history = self.history[: self._history_len]

        if not self._primed:
            self._primed = True
            _LOGGER.info("Primed with %d existing calls", len(self.history))

        # --- live ring detection ---
        try:
            state = await self._client.get_voice_state()
            txt = str(state).lower()
            ringing_now = "ringing" in txt or "incomingcall" in txt or "ring" in txt
            if ringing_now and not self._ringing:
                self._ringing = True
                self.hass.bus.async_fire(
                    EVENT_RING, {"last_call": self.history[0] if self.history else {}}
                )
            elif not ringing_now:
                self._ringing = False
        except LiveboxError:
            pass

        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        return {
            "calls": self.history,
            "last": self.history[0] if self.history else None,
            "count_today": sum(1 for c in self.history if str(c["timestamp"]).startswith(today)),
            "count_missed": sum(1 for c in self.history if c["direction"] == DIRECTION_MISSED),
            "count_incoming": sum(1 for c in self.history if c["direction"] == DIRECTION_INCOMING),
            "count_outgoing": sum(1 for c in self.history if c["direction"] == DIRECTION_OUTGOING),
            "contacts": self._contacts.all(),
            "ringing": self._ringing,
        }
