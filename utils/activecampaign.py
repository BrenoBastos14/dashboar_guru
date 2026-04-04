"""ActiveCampaign API v3 client."""

from __future__ import annotations

from typing import Any

import requests


class ActiveCampaignClient:
    """Thin wrapper around the ActiveCampaign REST API v3."""

    def __init__(self, account_url: str, api_key: str) -> None:
        # Normalise URL: strip trailing slash, ensure /api/3 suffix
        base = account_url.rstrip("/")
        if not base.endswith("/api/3"):
            base = base.rstrip("/") + "/api/3"
        self.base_url = base
        self.headers = {"Api-Token": api_key, "Content-Type": "application/json"}

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.get(url, headers=self.headers, params=params or {}, timeout=15)
        response.raise_for_status()
        return response.json()

    def test_connection(self) -> tuple[bool, str]:
        """Returns (success, message)."""
        try:
            data = self._get("accounts")
            return True, "Conexão estabelecida com sucesso!"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            if status == 401:
                return False, "API Key inválida ou sem permissão."
            return False, f"Erro HTTP {status}: {e}"
        except requests.exceptions.ConnectionError:
            return False, "Não foi possível conectar. Verifique a URL da conta."
        except Exception as e:  # noqa: BLE001
            return False, f"Erro inesperado: {e}"

    def list_automations(self) -> list[dict[str, Any]]:
        """Return all automations, handling pagination."""
        automations: list[dict] = []
        offset = 0
        limit = 100
        while True:
            data = self._get("automations", params={"limit": limit, "offset": offset})
            batch = data.get("automations", [])
            automations.extend(batch)
            meta = data.get("meta", {})
            total = int(meta.get("total", len(automations)))
            offset += limit
            if offset >= total or not batch:
                break
        return automations

    def get_automation(self, automation_id: int | str) -> dict[str, Any]:
        """Return a single automation by ID."""
        data = self._get(f"automations/{automation_id}")
        return data.get("automation", {})
