"""Async Livebox 5 sysbus client — auth, call list, and ring/voice state.

Verified against live Livebox 5 firmware:
  - Auth:  POST /ws  Content-Type application/x-sah-ws-4-call+json,
           Authorization: X-Sah-Login, service sah.Device.Information,
           method createContext -> {"status":0,"data":{"contextID": "..."}}
  - Calls: VoiceService.VoiceApplication:getCallList {} -> {"status":[...]}
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class LiveboxError(Exception):
    """Raised on Livebox API errors."""


class LiveboxAuthError(LiveboxError):
    """Raised when authentication fails."""


class LiveboxClient:
    """Minimal async sysbus client for a Livebox 4/5."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str,
        password: str,
    ) -> None:
        # Own session with an UNSAFE cookie jar — aiohttp drops cookies for
        # IP-address hosts (192.168.1.1) by default, which breaks the Livebox
        # session cookie and makes getCallList return null.
        self._owns_session = session is None
        self._session = session or aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        self._base = host.rstrip("/")
        self._user = username
        self._password = password
        self._context_id = None

    @property
    def authenticated(self) -> bool:
        return self._context_id is not None

    async def login(self) -> None:
        """Create a sysbus context (session cookie + contextID)."""
        url = f"{self._base}/ws"
        headers = {
            "Content-Type": "application/x-sah-ws-4-call+json",
            "Authorization": "X-Sah-Login",
        }
        payload = {
            "service": "sah.Device.Information",
            "method": "createContext",
            "parameters": {
                "applicationName": "webui",
                "username": self._user,
                "password": self._password,
            },
        }
        try:
            async with self._session.post(
                url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise LiveboxError(f"Connection error: {err}") from err

        ctx = (data.get("data") or {}).get("contextID") or data.get("contextID")
        if not ctx:
            raise LiveboxAuthError(f"Authentication failed: {data}")
        self._context_id = ctx
        _LOGGER.debug("Livebox context acquired")

    async def _call(
        self, service: str, method: str, parameters: dict | None = None
    ) -> dict[str, Any]:
        if self._context_id is None:
            await self.login()
        url = f"{self._base}/ws"
        headers = {
            "Content-Type": "application/x-sah-ws-4-call+json",
            "X-Context": self._context_id or "",
        }
        payload = {"service": service, "method": method, "parameters": parameters or {}}
        async with self._session.post(
            url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 401:
                self._context_id = None
                raise LiveboxAuthError("Session expired (401)")
            return await resp.json(content_type=None)

    async def get_calls(self) -> list[dict]:
        """Return the raw call list."""
        res = await self._call("VoiceService.VoiceApplication", "getCallList", {})
        calls = res.get("status")
        if isinstance(calls, list):
            return calls
        data = res.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("callList"), list):
            return data["callList"]
        return []

    async def get_voice_state(self) -> dict:
        """
        Return VoIP line state — used for live ring detection.
        Different firmware expose this differently; we try the common ones and
        return {} if unavailable (ring detection then degrades to call-list poll).
        """
        for service, method in (
            ("VoiceService.VoiceApplication", "getState"),
            ("VoiceService.VoiceApplication", "get"),
        ):
            try:
                res = await self._call(service, method, {})
                if isinstance(res.get("status"), (dict, list)):
                    return res
            except LiveboxError:
                continue
        return {}
