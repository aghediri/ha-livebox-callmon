"""Contact storage + CRUD + number normalisation.

Contacts are persisted in Home Assistant's storage (.storage/) keyed by a
canonical phone number, so +33162562353 and 0162562353 map to one contact.
"""

from __future__ import annotations

import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION, TAGS


def canon_number(raw: str, country_prefix: str = "33") -> str:
    """Canonicalise a phone number for matching."""
    if not raw:
        return ""
    n = re.sub(r"[^\d+]", "", str(raw))
    if n.startswith("+"):
        n = n[1:]
    elif n.startswith("00"):
        n = n[2:]
    elif n.startswith("0") and len(n) > 5:
        n = country_prefix + n[1:]
    return n


class ContactStore:
    """Async CRUD over HA storage."""

    def __init__(self, hass: HomeAssistant, country_prefix: str = "33") -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._country = country_prefix
        self._data: dict[str, dict] = {}

    async def load(self) -> None:
        self._data = await self._store.async_load() or {}

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    def all(self) -> list[dict]:
        out = []
        for key, c in sorted(
            self._data.items(), key=lambda kv: kv[1].get("name", "").lower()
        ):
            out.append(
                {
                    "key": key,
                    "number": c.get("number", key),
                    "name": c.get("name", ""),
                    "tag": c.get("tag", "other"),
                    "notes": c.get("notes", ""),
                }
            )
        return out

    def lookup(self, number: str) -> dict | None:
        return self._data.get(canon_number(number, self._country))

    async def add(self, number: str, name: str, tag: str = "other", notes: str = "") -> str:
        key = canon_number(number, self._country)
        if tag not in TAGS:
            tag = "other"
        self._data[key] = {"number": number, "name": name, "tag": tag, "notes": notes}
        await self._save()
        return key

    async def edit(self, number: str, **fields) -> bool:
        key = canon_number(number, self._country)
        if key not in self._data:
            return False
        c = self._data[key]
        if "name" in fields and fields["name"] is not None:
            c["name"] = fields["name"]
        if "tag" in fields and fields["tag"]:
            c["tag"] = fields["tag"] if fields["tag"] in TAGS else "other"
        if "notes" in fields and fields["notes"] is not None:
            c["notes"] = fields["notes"]
        if fields.get("new_number"):
            new_key = canon_number(fields["new_number"], self._country)
            c["number"] = fields["new_number"]
            if new_key != key:
                del self._data[key]
                key = new_key
        self._data[key] = c
        await self._save()
        return True

    async def delete(self, number: str) -> bool:
        key = canon_number(number, self._country)
        if key in self._data:
            del self._data[key]
            await self._save()
            return True
        return False
