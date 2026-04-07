import io
import re
import pandas as pd
import numpy as np


FB_COLUMN_ALIASES = {
    "campanha": ["Nome da campanha", "Campaign name", "Campanha"],
    "conjunto": [
        "Nome do conjunto de anúncios", "Nome do conjunto", "Conjunto de anúncios",
        "Ad set name", "Conjunto",
    ],
    "anuncio": ["Nome do anúncio", "Ad name", "Anúncio", "Anuncio"],
    "hora_do_dia": [
        "Hora do dia", "Hora do Dia", "Hora", "Hour of day",
        "Período (hora do dia)", "Periodo (hora do dia)",
        "Breakdown: Hour of day", "Hour",
    ],
    "gasto": [
        "Valor usado (BRL)", "Valor usado (BR)", "Valor usado",
        "Amount spent (BRL)", "Amount spent", "Spend",
        "Custo", "Cost",
    ],
    "data_inicio": [
        "Início dos relatórios", "Inicio dos relatorios", "Início", "Inicio",
        "Report start", "Start date", "Data",
    ],
    "data_fim": [
        "Término dos relatórios", "Termino dos relatorios", "Término", "Termino",
        "Report end", "End date",
    ],
}


def _find_fb_column(df: pd.DataFrame, key: str):
    lower_map = {c.lower(): c for c in df.columns}
    for candidate in FB_COLUMN_ALIASES.get(key, []):
        real = lower_map.get(candidate.lower())
        if real is not None:
            return real
    return None


def _parse_brl_number(series: pd.Series) -> pd.Series:
    """
    Convert monetary values to float.
    Handles:
      - Brazilian format: "1.234,56" → 1234.56
      - International/XLSX float: "27.21" or 27.21 → 27.21
      - Already numeric values from XLSX
    """
    def _convert(val):
        if pd.isna(val):
            return 0.0
        # Already a number (from XLSX)
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        # Remove currency symbol
        s = re.sub(r"R\$\s*", "", s)
        s = s.strip()
        if not s:
            return 0.0
        # Detect format: if has comma → Brazilian format
        # "1.234,56" or "27,21" → Brazilian (comma = decimal)
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        # else: "27.21" or "1234.56" → already correct international format
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    return series.apply(_convert)


def _parse_hora_do_dia(series: pd.Series) -> pd.Series:
    """
    Parse 'Hora do dia' column to integer hour (0-23).
    Handles formats exported by Meta Ads Manager:
      - '09:00:00 - 09:59'   → 9
      - '9:00 - 9:59'        → 9
      - '0 - 1'              → 0
      - '9'                  → 9
      - 9 (int/float)        → 9
    """
    def _extract(val):
        if pd.isna(val):
            return np.nan
        # Already numeric
        if isinstance(val, (int, float)):
            return int(val)
        s = str(val).strip()
        if not s or s.lower() in ("nan", "none", ""):
            return np.nan
        # "HH:MM:SS - ..." or "HH:MM - ..."  →  take leading digits before ':'
        m = re.match(r"^(\d{1,2})\s*:", s)
        if m:
            return int(m.group(1))
        # "0 - 1"  or  "9 - 10"  →  take first number
        m = re.match(r"^(\d{1,2})\s*[-–]", s)
        if m:
            return int(m.group(1))
        # Plain integer string
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return np.nan
    return series.apply(_extract)


def load_facebook_file(file) -> pd.DataFrame:
    """
    Load a Facebook Ads CSV or XLSX report file and normalize columns.
    Returns a DataFrame with internal column names:
      campanha, conjunto, anuncio, hora, gasto, data
    """
    name = getattr(file, "name", "") or ""

    if name.lower().endswith(".xlsx"):
        df = pd.read_excel(file, dtype=str, engine="openpyxl")
        df.columns = df.columns.str.strip()
    else:
        raw = file.read() if hasattr(file, "read") else open(file, "rb").read()
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("Não foi possível detectar o encoding do arquivo.")

        first_line = text.split("\n")[0]
        sep = ";" if first_line.count(";") > first_line.count(",") else ","
        df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str)
        df.columns = df.columns.str.strip()

    # Build rename map
    rename_map = {}
    for internal, aliases in FB_COLUMN_ALIASES.items():
        lower_map = {c.lower(): c for c in df.columns}
        for alias in aliases:
            real = lower_map.get(alias.lower())
            if real is not None and real not in rename_map:
                rename_map[real] = internal
                break

    df = df.rename(columns=rename_map).copy()

    # Parse gasto
    if "gasto" in df.columns:
        df["gasto"] = _parse_brl_number(df["gasto"])

    # Parse data
    if "data_inicio" in df.columns:
        df["data"] = pd.to_datetime(df["data_inicio"], dayfirst=True, errors="coerce")
    else:
        df["data"] = pd.NaT

    # Parse hora
    if "hora_do_dia" in df.columns:
        df["hora"] = _parse_hora_do_dia(df["hora_do_dia"])
    else:
        df["hora"] = np.nan

    # Clean string columns
    for col in ("campanha", "conjunto", "anuncio"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", pd.NA)

    return df


def _normalize_campaign(s: pd.Series) -> pd.Series:
    """Lowercase + strip for fuzzy campaign matching."""
    return s.astype(str).str.lower().str.strip()


def merge_fb_guru(df_fb: pd.DataFrame, df_guru: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-reference Facebook Ads spend with Guru Manager sales.

    Matching key: normalized campaign name + date + hour (from Guru's `data` column).
    The Guru sales rows get a `hora` column extracted from the `data` timestamp.

    Returns a merged DataFrame with columns:
      campanha, conjunto, anuncio, data, hora,
      gasto (FB), vendas (count), receita (sum from Guru),
      roas, cpa, taxa_conv
    """
    if df_fb.empty:
        return pd.DataFrame()

    # Prepare Guru side
    guru = df_guru.copy()
    if "data" in guru.columns:
        guru["_hora"] = guru["data"].dt.hour
        guru["_data"] = guru["data"].dt.normalize()
    else:
        guru["_hora"] = np.nan
        guru["_data"] = pd.NaT

    # Normalize campaign name for matching
    has_campaign_guru = "utm_campaign" in guru.columns
    if has_campaign_guru:
        guru["_campanha_norm"] = _normalize_campaign(guru["utm_campaign"].fillna(""))
    else:
        guru["_campanha_norm"] = ""

    # Aggregate Guru sales by campaign + date + hour
    guru_agg = (
        guru.groupby(["_campanha_norm", "_data", "_hora"])
        .agg(
            vendas=("valor", "count"),
            receita=("valor", "sum"),
        )
        .reset_index()
    )

    # Prepare FB side
    fb = df_fb.copy()
    fb["_campanha_norm"] = _normalize_campaign(fb["campanha"].fillna("") if "campanha" in fb.columns else "")
    if "data" in fb.columns:
        fb["_data"] = pd.to_datetime(fb["data"]).dt.normalize()
    else:
        fb["_data"] = pd.NaT

    fb["_hora"] = fb["hora"] if "hora" in fb.columns else np.nan

    # Merge
    merged = fb.merge(
        guru_agg,
        on=["_campanha_norm", "_data", "_hora"],
        how="left",
    )
    merged["vendas"] = merged["vendas"].fillna(0).astype(int)
    merged["receita"] = merged["receita"].fillna(0.0)

    # Metrics
    merged["roas"] = merged.apply(
        lambda r: r["receita"] / r["gasto"] if r.get("gasto", 0) > 0 else 0.0, axis=1
    )
    merged["cpa"] = merged.apply(
        lambda r: r["gasto"] / r["vendas"] if r.get("vendas", 0) > 0 else 0.0, axis=1
    )

    return merged


def aggregate_fb_metrics(df_merged: pd.DataFrame, group_by: list) -> pd.DataFrame:
    """
    Aggregate merged FB+Guru data by the specified group columns.
    Returns DataFrame with: group cols, Gasto, Vendas, Receita, ROAS, CPA.
    """
    if df_merged.empty:
        return pd.DataFrame()

    agg_cols = {c: c for c in group_by if c in df_merged.columns}
    present = [c for c in group_by if c in df_merged.columns]

    if not present:
        return pd.DataFrame()

    grp = df_merged.groupby(present, dropna=False).agg(
        gasto=("gasto", "sum"),
        vendas=("vendas", "sum"),
        receita=("receita", "sum"),
    ).reset_index()

    grp["roas"] = grp.apply(
        lambda r: round(r["receita"] / r["gasto"], 2) if r["gasto"] > 0 else 0.0, axis=1
    )
    grp["cpa"] = grp.apply(
        lambda r: round(r["gasto"] / r["vendas"], 2) if r["vendas"] > 0 else 0.0, axis=1
    )

    grp = grp.sort_values("gasto", ascending=False).reset_index(drop=True)
    return grp
