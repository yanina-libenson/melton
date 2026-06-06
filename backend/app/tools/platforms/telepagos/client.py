"""Minimal client for the TelePagos Empresas API (vendored into Melton).

Source: ~/Code/Repos/Personal/telepagos-agent/client.py. Credentials are the
API username/password (Plataforma Web -> API section), NOT the web login.
Sync httpx client; the tool calls it via asyncio.to_thread.
"""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from datetime import datetime

import httpx

BASE_URLS = {
    "homo": "https://api.homo.telepagos.com.ar",  # homologacion (sandbox)
    "prod": "https://api.telepagos.com.ar",
}


class TelePagosError(Exception):
    """The API responded with status=error."""


def _parse_expires_at(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp()


@dataclass
class _Token:
    value: str
    expires_at: float

    @property
    def is_valid(self) -> bool:
        return bool(self.value) and time.time() < self.expires_at - 60


class TelePagos:
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        env: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._username = username or os.environ["TELEPAGOS_USERNAME"]
        self._password = password or os.environ["TELEPAGOS_PASSWORD"]
        env = env or os.environ.get("TELEPAGOS_ENV", "homo")
        if env not in BASE_URLS:
            raise ValueError(f"env debe ser uno de {list(BASE_URLS)}, no {env!r}")
        self._http = httpx.Client(base_url=BASE_URLS[env], timeout=timeout)
        self._token: _Token | None = None

    def _authenticate(self) -> None:
        payload = self._request(
            "POST",
            "v2/auth/token",
            json={"username": self._username, "password": self._password},
            auth=False,
        )
        self._token = _Token(value=payload["token"], expires_at=_parse_expires_at(payload["expires_at"]))

    def _auth_header(self) -> dict[str, str]:
        if self._token is None or not self._token.is_valid:
            self._authenticate()
        assert self._token is not None
        return {"Authorization": f"Bearer {self._token.value}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        auth: bool = True,
    ) -> dict:
        headers = self._auth_header() if auth else {}
        resp = self._http.request(method, path, json=json, params=params, headers=headers)
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise
        if isinstance(data, dict) and data.get("status") == "error":
            raise TelePagosError(data.get("message", "error desconocido"))
        resp.raise_for_status()
        return data

    def balance(self) -> int:
        """Available account balance (GET v2/account/balance)."""
        return self._request("GET", "v2/account/balance")["amount"]

    def cashout(
        self,
        *,
        amount: float,
        cuit: str,
        reference_id: str,
        concept: str,
        description: str = "",
        cvu: str | None = None,
        alias: str | None = None,
    ) -> str:
        """Send a transfer to a CVU/CBU or alias (POST v2/payment/cashout).

        reference_id must be unique and idempotent: reuse the same reference_id
        to retry/look up the same payment. Returns the operation id.
        """
        if bool(cvu) == bool(alias):
            raise ValueError("Envia cvu O alias, no ambos ni ninguno.")
        body = {
            "cuit": cuit,
            "amount": amount,
            "reference_id": reference_id,
            "concept": concept,
            "description": description,
        }
        body["cvu" if cvu else "alias"] = cvu or alias
        return self._request("POST", "v2/payment/cashout", json=body)["id"]

    def cashout_voucher(self, transfer_id: str) -> str:
        """Transfer receipt as a base64-encoded PDF (GET v2/payment/cashout/{id})."""
        return self._request("GET", f"v2/payment/cashout/{transfer_id}")["voucher"]

    def save_voucher(self, transfer_id: str, path: str) -> str:
        pdf = base64.b64decode(self.cashout_voucher(transfer_id))
        with open(path, "wb") as f:
            f.write(pdf)
        return path

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "TelePagos":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
