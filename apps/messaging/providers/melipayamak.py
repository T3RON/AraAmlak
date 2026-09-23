"""
MeliPayamak SMS adapter.

Official docs: https://www.melipayamak.com/api/

Endpoints (REST/JSON flavour):
  POST https://rest.payamak-panel.com/api/SendSMS/SendSMS
  POST https://rest.payamak-panel.com/api/SendSMS/GetSMSDeliveries2
  POST https://rest.payamak-panel.com/api/SendSMS/GetCredit

Auth: username + password in request body (no Bearer token).
"""

from __future__ import annotations

import logging
from decimal import Decimal

import requests

from .base import SMSProvider

logger = logging.getLogger(__name__)

_BASE = "https://rest.payamak-panel.com/api/SendSMS"
_TIMEOUT = 10


class MeliPayamakSMSProvider(SMSProvider):
    """
    Adapter for the MeliPayamak (ملی‌پیامک) Iranian SMS gateway.

    Parameters
    ----------
    username : str  — panel username
    password : str  — panel password (stored encrypted in AgencySMSConfig)
    sender   : str  — default line number
    """

    def __init__(self, username: str, password: str, sender: str = "") -> None:
        self._username = username
        self._password = password
        self._sender = sender

    def _auth(self) -> dict:
        return {"username": self._username, "password": self._password}

    def send(self, to: str, text: str, sender: str | None = None) -> str:
        line = sender or self._sender
        payload = {
            **self._auth(),
            "to": to,
            "from": line,
            "text": text,
            "isFlash": False,
        }
        resp = requests.post(f"{_BASE}/SendSMS", json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        ret_code = data.get("RetStatus")
        if ret_code != 1:
            raise RuntimeError(f"MeliPayamak error {ret_code}: {data.get('StrRetStatus')}")
        message_id = str(data["Value"])
        masked = ("*" * (len(to) - 4) + to[-4:]) if len(to) > 4 else to
        logger.info("[MeliPayamak] sent to=%s id=%s", masked, message_id)
        return message_id

    def status(self, message_id: str) -> str:
        payload = {**self._auth(), "MsgId": message_id, "From": self._sender}
        resp = requests.post(f"{_BASE}/GetSMSDeliveries2", json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        # API returns an int status; convert to string for uniformity
        return str(data.get("Value", "unknown"))

    def balance(self) -> Decimal:
        payload = self._auth()
        resp = requests.post(f"{_BASE}/GetCredit", json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return Decimal(str(data.get("Value", "0")))
