import streamlit as st
import pandas as pd

from utils.data_processor import load_csv, clean_data, filter_data

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Guru Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar — upload
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://img.icons8.com/color/96/combo-chart--v1.png",
        width=60,
    )
    st.title("Guru Manager")
    st.caption("Dashboard de Vendas")
    st.divider()

    uploaded_file = st.file_uploader(
        "Carregar CSV",
        type=["csv"],
        help="Exporte o relatório de vendas no Guru Manager e faça upload aqui.",
    )

    st.divider()
    st.subheader("Filtros")

# ---------------------------------------------------------------------------
# Estado principal
# ---------------------------------------------------------------------------
if uploaded_file is None:
    st.markdown("## 📊 Dashboard de Vendas — Guru Manager")
    st.info(
        "**Para começar, faça upload do arquivo CSV** exportado do Guru Manager "
        "usando o painel lateral à esquerda.\n\n"
        "**Como exportar?**\n"
        "1. Acesse o painel do Guru Manager\n"
        "2. Vá em **Relatórios → Vendas**\n"
        "3. Aplique os filtros desejados\n"
        "4. Clique em **Exportar CSV**\n"
        "5. Faça upload do arquivo aqui",
        icon="💡",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Carrega e processa dados
# ---------------------------------------------------------------------------
try:
    df_raw = load_csv(uploaded_file)
    df = clean_data(df_raw)
except Exception as e:
    st.error(f"Erro ao processar o arquivo: {e}")
    st.stop()

if df.empty:
    st.warning("O arquivo CSV está vazio ou não contém dados válidos.")
    st.stop()

# ---------------------------------------------------------------------------
# Filtros na sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    # Filtro de período
    if "data" in df.columns:
        min_date = df["data"].min().date()
        max_date = df["data"].max().date()
        start_date = st.date_input("Data inicial", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("Data final", value=max_date, min_value=min_date, max_value=max_date)
    else:
        start_date = end_date = None

    # Filtro de status
    status_opts = sorted(df["status"].dropna().unique().tolist()) if "status" in df.columns else []
    selected_status = st.multiselect("Status", options=status_opts, default=status_opts)

    # Filtro de produto
    produto_opts = sorted(df["produto"].dropna().unique().tolist()) if "produto" in df.columns else []
    selected_produtos = st.multiselect("Produto", options=produto_opts, default=produto_opts)

    # Filtros de Origem / UTM
    _utm_filtros = [
        ("origem_3",    "Origem 3"),
        ("utm_source",  "UTM Source"),
        ("utm_campaign","UTM Campaign"),
        ("utm_medium",  "UTM Medium"),
        ("utm_content", "UTM Content"),
    ]
    _utm_has_any = any(c in df.columns for c, _ in _utm_filtros)
    if _utm_has_any:
        st.divider()
        st.markdown("**Origem / UTM**")

    utm_selected = {}
    for campo, label in _utm_filtros:
        if campo in df.columns:
            opts = sorted(df[campo].dropna().unique().tolist())
            utm_selected[campo] = st.multiselect(label, options=opts, default=opts)
        else:
            utm_selected[campo] = None

# ---------------------------------------------------------------------------
# Aplica filtros
# ---------------------------------------------------------------------------
df_filtered = filter_data(
    df,
    start_date=start_date,
    end_date=end_date,
    status_list=selected_status if selected_status else None,
    produtos_list=selected_produtos if selected_produtos else None,
    origem_3_list=utm_selected.get("origem_3") or None,
    utm_source_list=utm_selected.get("utm_source") or None,
    utm_campaign_list=utm_selected.get("utm_campaign") or None,
    utm_medium_list=utm_selected.get("utm_medium") or None,
    utm_content_list=utm_selected.get("utm_content") or None,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("## 📊 Dashboard de Vendas — Guru Manager")
st.caption(f"Exibindo **{len(df_filtered):,}** registros")
st.divider()

# ---------------------------------------------------------------------------
# Tabela de Transações
# ---------------------------------------------------------------------------
st.subheader("Transações Detalhadas")

display_cols = [c for c in [
    "data", "codigo", "contato", "produto", "valor", "metodo_pagamento", "status",
    "origem_3", "utm_source", "utm_campaign", "utm_medium", "utm_content",
] if c in df_filtered.columns]

col_labels = {
    "data": "Data",
    "codigo": "Código",
    "contato": "Cliente",
    "produto": "Produto",
    "valor": "Valor (R$)",
    "metodo_pagamento": "Pagamento",
    "status": "Status",
    "origem_3": "Origem 3",
    "utm_source": "UTM Source",
    "utm_campaign": "UTM Campaign",
    "utm_medium": "UTM Medium",
    "utm_content": "UTM Content",
}

df_display = df_filtered[display_cols].copy()
if "data" in df_display.columns:
    df_display["data"] = df_display["data"].dt.strftime("%d/%m/%Y %H:%M")
if "valor" in df_display.columns:
    df_display["valor"] = df_display["valor"].apply(
        lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

df_display = df_display.rename(columns=col_labels)

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
    height=600,
)

st.caption(f"Total de {len(df_filtered):,} registros exibidos.")
