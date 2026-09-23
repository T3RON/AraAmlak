"""
Kavenegar SMS adapter.

Official docs: https://kavenegar.com/rest.html

Endpoints used:
  POST https://api.kavenegar.com/v1/{apikey}/sms/send.json
  POST https://api.kavenegar.com/v1/{apikey}/sms/status.json
  GET  https://api.kavenegar.com/v1/{apikey}/account/info.json

All requests use HTTP Basic auth via the API key embedded in the URL path
(Kavenegar convention).  The adapter uses `requests` — available in the
project's dependencies.

Error codes reference:
  200 OK, 400 bad param, 401 bad API key, 402 insufficient credit,
  403 sender not available, 404 no result, 409 limit exceeded, 500 server error.
"""

from __future__ import annotations

import logging
from decimal import Decimal

import requests

from .base import SMSProvider

logger = logging.getLogger(__name__)

_BASE = "https://api.kavenegar.com/v1/{apikey}"
_TIMEOUT = 10  # seconds


class KavenegarSMSProvider(SMSProvider):
    """
    Adapter for the Kavenegar (کاوه‌نگار) Iranian SMS gateway.

    Parameters
    ----------
    api_key : str   — provider API key (stored encrypted in AgencySMSConfig)
    sender  : str   — default line number (e.g. "1000xxx")
    """

    def __init__(self, api_key: str, sender: str = "") -> None:
        self._api_key = api_key
        self._sender = sender
        self._base = _BASE.format(apikey=api_key)

    def send(self, to: str, text: str, sender: str | None = None) -> str:
        line = sender or self._sender
        payload: dict = {"receptor": to, "message": text}
        if line:
            payload["sender"] = line

        resp = requests.post(
            f"{self._base}/sms/send.json",
            data=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        entries = data.get("return", {})
        if entries.get("status") != 200:
            raise RuntimeError(
                f"Kavenegar error {entries.get('status')}: {entries.get('message')}"
            )
        message_id = str(data["entries"][0]["messageid"])
        # Log only last-4 of recipient
        masked = ("*" * (len(to) - 4) + to[-4:]) if len(to) > 4 else to
        logger.info("[Kavenegar] sent to=%s id=%s", masked, message_id)
        return message_id

    def status(self, message_id: str) -> str:
        resp = requests.post(
            f"{self._base}/sms/status.json",
            data={"messageid": message_id},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        entries = data.get("entries", [])
        if not entries:
            return "unknown"
        return str(entries[0].get("status", "unknown"))

    def balance(self) -> Decimal:
        resp = requests.get(
            f"{self._base}/account/info.json",
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return Decimal(str(data["entries"]["remaincredit"]))

    def send_bulk(self, recipients: list[str], text: str, sender: str | None = None) -> list[str]:
        """Use Kavenegar bulk endpoint for efficiency."""
        line = sender or self._sender
        payload: dict = {
            "receptor": ",".join(recipients),
            "message": text,
        }
        if line:
            payload["sender"] = line

        resp = requests.post(
            f"{self._base}/sms/sendarray.json",
            data=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        entries = data.get("return", {})
        if entries.get("status") != 200:
            raise RuntimeError(
                f"Kavenegar bulk error {entries.get('status')}: {entries.get('message')}"
            )
        return [str(e["messageid"]) for e in data["entries"]]
