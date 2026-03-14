"""
Facebook / Meta Ads Marketing API — utilitários de integração.
Versão API: v19.0
"""

import requests
import streamlit as st

_API_VERSION = "v19.0"
_BASE_URL = f"https://graph.facebook.com/{_API_VERSION}"

_INSIGHTS_FIELDS = (
    "campaign_name,spend,impressions,clicks,ctr,cpc,reach"
)


def fetch_ad_accounts(access_token: str) -> list[dict]:
    """
    Retorna as contas de anúncios associadas ao token de acesso.
    Cada item: {"id": "act_XXXXX", "name": "..."}
    """
    url = f"{_BASE_URL}/me/adaccounts"
    params = {
        "access_token": access_token,
        "fields": "id,name,account_status,currency",
        "limit": 50,
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


@st.cache_data(ttl=300)
def fetch_campaign_insights(
    access_token: str,
    ad_account_id: str,
    date_preset: str = "last_30d",
) -> list[dict]:
    """
    Retorna métricas de campanha para a conta informada.
    date_preset: 'last_7d' | 'last_30d' | 'this_month' | 'last_month'
    """
    # Garante prefixo act_
    account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"

    url = f"{_BASE_URL}/{account_id}/insights"
    params = {
        "access_token": access_token,
        "fields": _INSIGHTS_FIELDS,
        "level": "campaign",
        "date_preset": date_preset,
        "limit": 200,
    }

    rows: list[dict] = []
    while True:
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            error = resp.json().get("error", {})
            raise RuntimeError(
                f"Erro {resp.status_code}: {error.get('message', resp.text)}"
            )
        payload = resp.json()
        rows.extend(payload.get("data", []))

        # Paginação
        next_url = payload.get("paging", {}).get("next")
        if not next_url:
            break
        # Próxima página usa a URL completa diretamente
        resp2 = requests.get(next_url, timeout=20)
        resp2.raise_for_status()
        payload = resp2.json()
        rows.extend(payload.get("data", []))
        if not payload.get("paging", {}).get("next"):
            break

    return rows


def parse_insights_to_df(rows: list[dict]):
    """Converte lista de insights para DataFrame com tipos corretos."""
    import pandas as pd

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    numeric_cols = ["spend", "impressions", "clicks", "ctr", "cpc", "reach"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df
