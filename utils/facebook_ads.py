"""Integração com a Marketing API do Facebook (Meta)."""
import requests
import pandas as pd

_BASE_URL = "https://graph.facebook.com/v19.0"

# Campos buscados por campanha
_FIELDS = "campaign_name,spend,impressions,clicks,ctr,cpc,reach"


def fetch_campaign_insights(
    access_token: str,
    ad_account_id: str,
    since: str,
    until: str,
) -> pd.DataFrame:
    """
    Busca insights de campanhas no período indicado.

    Parâmetros
    ----------
    access_token : str
        Token de acesso com permissão ``ads_read``.
    ad_account_id : str
        ID da conta de anúncios. Aceita com ou sem prefixo ``act_``.
    since : str
        Data de início no formato ``YYYY-MM-DD``.
    until : str
        Data de fim no formato ``YYYY-MM-DD``.

    Retorna
    -------
    pd.DataFrame com colunas:
        campaign_name, spend, impressions, clicks, ctr, cpc, reach
    """
    account = (
        ad_account_id
        if str(ad_account_id).startswith("act_")
        else f"act_{ad_account_id}"
    )
    url = f"{_BASE_URL}/{account}/insights"
    params = {
        "fields": _FIELDS,
        "level": "campaign",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "limit": 500,
        "access_token": access_token,
    }

    rows = []
    while url:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()

        if "error" in payload:
            err = payload["error"]
            raise ValueError(f"Facebook API error {err.get('code')}: {err.get('message')}")

        rows.extend(payload.get("data", []))
        url = payload.get("paging", {}).get("next")
        params = {}  # next URL já contém todos os parâmetros

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    for col in ["spend", "impressions", "clicks", "ctr", "cpc", "reach"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df
