"""
Facebook / Meta Ads Marketing API — utilitários de integração.
Versão API: v19.0
"""

import requests
import streamlit as st

_API_VERSION = "v19.0"
_BASE_URL = f"https://graph.facebook.com/{_API_VERSION}"

_INSIGHTS_FIELDS = (
    "campaign_name,spend,impressions,clicks,ctr,cpc,reach,frequency"
)

_INSIGHTS_FIELDS_DAILY = (
    "campaign_name,spend,impressions,clicks,ctr,cpc,reach"
)


def fetch_ad_accounts(access_token: str) -> list[dict]:
    """Retorna as contas de anúncios associadas ao token de acesso."""
    url = f"{_BASE_URL}/me/adaccounts"
    params = {
        "access_token": access_token,
        "fields": "id,name,account_status,currency",
        "limit": 50,
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", [])


def _paginate(url: str, params: dict) -> list[dict]:
    """Itera todas as páginas de resultados."""
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
        next_url = payload.get("paging", {}).get("next")
        if not next_url:
            break
        # Próximas páginas usam a URL completa (já contém access_token)
        params = {}
        url = next_url
    return rows


@st.cache_data(ttl=300)
def fetch_campaign_insights(
    access_token: str,
    ad_account_id: str,
    date_preset: str = "last_30d",
) -> list[dict]:
    """
    Retorna métricas agregadas por campanha.
    date_preset: 'last_7d' | 'last_30d' | 'this_month' | 'last_month'
    """
    account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
    url = f"{_BASE_URL}/{account_id}/insights"
    params = {
        "access_token": access_token,
        "fields": _INSIGHTS_FIELDS,
        "level": "campaign",
        "date_preset": date_preset,
        "limit": 200,
    }
    return _paginate(url, params)


@st.cache_data(ttl=300)
def fetch_campaign_insights_daily(
    access_token: str,
    ad_account_id: str,
    date_preset: str = "last_30d",
) -> list[dict]:
    """
    Retorna métricas por campanha com breakdown diário (time_increment=1).
    """
    account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
    url = f"{_BASE_URL}/{account_id}/insights"
    params = {
        "access_token": access_token,
        "fields": _INSIGHTS_FIELDS_DAILY,
        "level": "campaign",
        "date_preset": date_preset,
        "time_increment": 1,
        "limit": 500,
    }
    return _paginate(url, params)


def parse_insights_to_df(rows: list[dict]):
    """Converte lista de insights para DataFrame com tipos corretos."""
    import pandas as pd

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    numeric_cols = ["spend", "impressions", "clicks", "ctr", "cpc", "reach", "frequency"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def parse_daily_insights_to_df(rows: list[dict]):
    """Converte insights diários para DataFrame com coluna 'date' como datetime."""
    import pandas as pd

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    numeric_cols = ["spend", "impressions", "clicks", "ctr", "cpc", "reach"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "date_start" in df.columns:
        df["date"] = pd.to_datetime(df["date_start"])

    return df


def enrich_with_sales(df_fb, df_sales):
    """
    Cruza df_fb (insights do Facebook) com df_sales (vendas do CSV) por campaign_name × utm_campaign.
    Retorna df_fb com colunas: receita, vendas, ROAS, CPA, conv_rate.
    """
    import pandas as pd

    df = df_fb.copy()

    if "utm_campaign" in df_sales.columns and "valor" in df_sales.columns:
        sales_grp = (
            df_sales[df_sales["utm_campaign"].notna()]
            .groupby("utm_campaign")["valor"]
            .agg(receita="sum", vendas="count")
            .reset_index()
            .rename(columns={"utm_campaign": "campaign_name"})
        )
        df = df.merge(sales_grp, on="campaign_name", how="left")
    else:
        df["receita"] = 0.0
        df["vendas"] = 0

    df["receita"] = df["receita"].fillna(0)
    df["vendas"] = df["vendas"].fillna(0).astype(int)
    df["ROAS"] = df.apply(lambda r: r["receita"] / r["spend"] if r["spend"] > 0 else 0, axis=1)
    df["CPA"] = df.apply(lambda r: r["spend"] / r["vendas"] if r["vendas"] > 0 else 0, axis=1)
    df["conv_rate"] = df.apply(lambda r: r["vendas"] / r["clicks"] * 100 if r["clicks"] > 0 else 0, axis=1)

    return df
