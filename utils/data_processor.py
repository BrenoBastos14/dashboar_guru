import io
import pandas as pd
import numpy as np


# Mapeamento flexível de colunas do Guru Manager para nomes internos
COLUMN_ALIASES = {
    "data": ["Criada em", "Data", "Data da Venda", "Data do Pedido", "created_at"],
    "codigo": ["Código", "Codigo", "ID", "Pedido", "Order"],
    "contato": ["Contato", "Cliente", "Nome", "Customer", "Nome do Cliente"],
    "produto": ["Produto", "Product", "Nome do Produto"],
    "valor": ["Valor", "Value", "Total", "Preço", "Preco", "Valor Total"],
    "metodo_pagamento": [
        "Método de Pagamento",
        "Metodo de Pagamento",
        "Forma de Pagamento",
        "Payment Method",
        "Pagamento",
    ],
    "status": ["Status", "Estado", "Situação", "Situacao"],
    "aprovada_em": ["Aprovada em", "Aprovado em", "Data de Aprovação"],
    "cancelada_em": ["Cancelada em", "Cancelado em", "Data de Cancelamento"],
    "origem_3": ["Origem 3", "origem 3", "Origem3", "Source 3"],
    "utm_source": ["UTM Source", "utm_source", "Utm Source", "UTM source"],
    "utm_campaign": ["UTM Campaign", "utm_campaign", "Utm Campaign", "UTM campaign"],
    "utm_medium": ["UTM Medium", "utm_medium", "Utm Medium", "UTM medium"],
    "utm_content": ["UTM Content", "utm_content", "Utm Content", "UTM content"],
}

STATUS_APROVADO = {"aprovado", "aprovada", "completa", "completo", "pago", "paga"}


def load_csv(file) -> pd.DataFrame:
    """
    Lê um arquivo CSV do Guru Manager com detecção automática de encoding e separador.
    Aceita file-like objects (UploadedFile do Streamlit) ou caminhos de arquivo.
    """
    raw = file.read() if hasattr(file, "read") else open(file, "rb").read()

    # Tenta encodings comuns
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Não foi possível detectar o encoding do arquivo CSV.")

    # Detecta separador (ponto-e-vírgula ou vírgula)
    first_line = text.split("\n")[0]
    sep = ";" if first_line.count(";") > first_line.count(",") else ","

    df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str)
    df.columns = df.columns.str.strip()
    return df


def _find_column(df: pd.DataFrame, key: str):
    """Retorna o nome real da coluna no DataFrame para uma chave interna."""
    for candidate in COLUMN_ALIASES.get(key, []):
        if candidate in df.columns:
            return candidate
    return None


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza o DataFrame do Guru Manager:
    - Renomeia colunas para nomes internos
    - Converte 'Valor' de 'R$ 299,90' para float
    - Parseia 'data' como datetime
    """
    rename_map = {}
    for internal_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = internal_name
                break

    df = df.rename(columns=rename_map).copy()

    # Converte valor monetário
    if "valor" in df.columns:
        df["valor"] = (
            df["valor"]
            .astype(str)
            .str.replace(r"R\$\s*", "", regex=True)
            .str.replace(r"\.", "", regex=True)   # remove separador de milhar
            .str.replace(",", ".", regex=False)    # troca decimal
            .str.strip()
        )
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)

    # Converte datas
    for date_col in ("data", "aprovada_em", "cancelada_em"):
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(
                df[date_col], dayfirst=True, errors="coerce"
            )

    # Remove linhas sem data ou valor
    if "data" in df.columns:
        df = df.dropna(subset=["data"])

    return df


def filter_data(
    df: pd.DataFrame,
    start_date=None,
    end_date=None,
    status_list=None,
    produtos_list=None,
    origem_3_list=None,
    utm_source_list=None,
    utm_campaign_list=None,
    utm_medium_list=None,
    utm_content_list=None,
) -> pd.DataFrame:
    """Aplica filtros combinados ao DataFrame."""
    mask = pd.Series([True] * len(df), index=df.index)

    if start_date is not None and "data" in df.columns:
        mask &= df["data"] >= pd.Timestamp(start_date)

    if end_date is not None and "data" in df.columns:
        mask &= df["data"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    if status_list and "status" in df.columns:
        mask &= df["status"].isin(status_list)

    if produtos_list and "produto" in df.columns:
        mask &= df["produto"].isin(produtos_list)

    for col, val_list in [
        ("origem_3", origem_3_list),
        ("utm_source", utm_source_list),
        ("utm_campaign", utm_campaign_list),
        ("utm_medium", utm_medium_list),
        ("utm_content", utm_content_list),
    ]:
        if val_list and col in df.columns:
            mask &= df[col].isin(val_list)

    return df[mask].copy()


def compute_kpis(df: pd.DataFrame) -> dict:
    """Calcula os KPIs principais da dashboard."""
    num_vendas = len(df)
    receita_total = df["valor"].sum() if "valor" in df.columns else 0.0
    ticket_medio = receita_total / num_vendas if num_vendas > 0 else 0.0

    taxa_aprovacao = 0.0
    if "status" in df.columns and num_vendas > 0:
        aprovadas = df["status"].str.lower().isin(STATUS_APROVADO).sum()
        taxa_aprovacao = aprovadas / num_vendas * 100

    return {
        "receita_total": receita_total,
        "num_vendas": num_vendas,
        "ticket_medio": ticket_medio,
        "taxa_aprovacao": taxa_aprovacao,
    }
