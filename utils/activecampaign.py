"""ActiveCampaign API v3 client."""

from __future__ import annotations

from typing import Any

import requests


class ActiveCampaignClient:
    """Thin wrapper around the ActiveCampaign REST API v3."""

    def __init__(self, account_url: str, api_key: str) -> None:
        base = account_url.rstrip("/")
        if not base.endswith("/api/3"):
            base = base + "/api/3"
        self.base_url = base
        self.api_key = api_key

    @property
    def _get_headers(self) -> dict:
        return {"Api-Token": self.api_key, "Accept": "application/json"}

    @property
    def _post_headers(self) -> dict:
        return {"Api-Token": self.api_key, "Accept": "application/json", "Content-Type": "application/json"}

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.get(url, headers=self._get_headers, params=params or {}, timeout=15)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.post(url, headers=self._post_headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Diagnostics & connection
    # ------------------------------------------------------------------

    def diagnose(self) -> dict[str, Any]:
        """Test each endpoint and return status codes."""
        results = {}
        for ep in ("users/me", "tags?limit=1", "lists?limit=1", "automations?limit=1"):
            url = f"{self.base_url}/{ep.lstrip('/')}"
            try:
                r = requests.get(url, headers=self._get_headers, timeout=10)
                results[ep] = {"status": r.status_code, "ok": r.ok, "url": url}
            except Exception as e:  # noqa: BLE001
                results[ep] = {"status": "erro", "ok": False, "url": url, "erro": str(e)}
        return results

    def test_connection(self) -> tuple[bool, str]:
        """Returns (success, message). Tries multiple endpoints for compatibility."""
        for endpoint in ("users/me", "tags?limit=1", "lists?limit=1"):
            try:
                data = self._get(endpoint)
                name = data.get("user", {}).get("firstName", "") if endpoint == "users/me" else ""
                suffix = f" Olá, {name}!" if name else ""
                return True, f"Conectado com sucesso!{suffix}"
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else 0
                if status == 401:
                    return False, "API Key inválida. Verifique a chave e tente novamente."
                if status == 403:
                    return False, "Acesso negado (403). Verifique as permissões da API Key."
                continue
            except requests.exceptions.ConnectionError:
                return False, "Não foi possível conectar. Verifique a URL (ex: https://suaconta.api-us1.com)."
            except Exception as e:  # noqa: BLE001
                return False, f"Erro inesperado: {e}"
        return False, "Não foi possível verificar a conexão. Verifique a URL e a API Key."

    # ------------------------------------------------------------------
    # Automations
    # ------------------------------------------------------------------

    def list_automations(self) -> list[dict[str, Any]]:
        """Return all automations, handling pagination."""
        automations: list[dict] = []
        offset = 0
        limit = 100
        while True:
            try:
                data = self._get("automations", params={"limit": limit, "offset": offset})
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else 0
                if status == 405:
                    raise RuntimeError(
                        "Endpoint /automations retornou 405. Use o Diagnóstico na sidebar para mais detalhes."
                    ) from e
                raise
            batch = data.get("automations", [])
            automations.extend(batch)
            total = int(data.get("meta", {}).get("total", len(automations)))
            offset += limit
            if offset >= total or not batch:
                break
        return automations

    def get_automation(self, automation_id: int | str) -> dict[str, Any]:
        data = self._get(f"automations/{automation_id}")
        return data.get("automation", {})

    def create_automation(self, name: str, status: int = 1) -> dict[str, Any]:
        payload = {"automation": {"name": name, "status": str(status)}}
        try:
            data = self._post("automations", payload)
        except requests.exceptions.HTTPError as e:
            if (e.response.status_code if e.response else 0) == 405:
                raise RuntimeError("PLAN_LIMIT_405") from e
            raise
        return data.get("automation", {})

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def list_tags(self) -> list[dict[str, Any]]:
        tags: list[dict] = []
        offset = 0
        limit = 100
        while True:
            data = self._get("tags", params={"limit": limit, "offset": offset})
            batch = data.get("tags", [])
            tags.extend(batch)
            total = int(data.get("meta", {}).get("total", len(tags)))
            offset += limit
            if offset >= total or not batch:
                break
        return tags

    def create_tag(self, name: str, tag_type: str = "contact", description: str = "") -> dict[str, Any]:
        payload = {"tag": {"tag": name, "tagType": tag_type, "description": description}}
        data = self._post("tags", payload)
        return data.get("tag", {})
