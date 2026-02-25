import streamlit as st
import pandas as pd

from utils.data_processor import load_csv, clean_data, filter_data, compute_kpis
from utils.charts import (
    chart_receita_por_periodo,
    chart_vendas_por_produto,
    chart_distribuicao_status,
    chart_metodo_pagamento,
    chart_receita_por_campo,
)

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Guru Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS customizado para cards KPI
st.markdown(
    """
    <style>
    .kpi-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .kpi-label {
        font-size: 13px;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #1E293B;
    }
    .kpi-icon {
        font-size: 20px;
        margin-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def kpi_card(icon: str, label: str, value: str):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar
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
# Filtros na sidebar (preenchidos após carregar os dados)
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

    # Agrupamento temporal
    st.divider()
    agrupamento = st.radio(
        "Agrupar receita por",
        options=["D", "W", "ME"],
        format_func=lambda x: {"D": "Dia", "W": "Semana", "ME": "Mês"}[x],
        horizontal=True,
        index=0,
    )

    # Top N produtos
    top_n = st.slider("Top N produtos", min_value=5, max_value=20, value=10, step=1)

# ---------------------------------------------------------------------------
# Aplica filtros
# ---------------------------------------------------------------------------
df_filtered = filter_data(
    df,
    start_date=start_date,
    end_date=end_date,
    status_list=selected_status if selected_status else None,
    produtos_list=selected_produtos if selected_produtos else None,
)

kpis = compute_kpis(df_filtered)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("## 📊 Dashboard de Vendas — Guru Manager")
st.caption(
    f"Exibindo **{kpis['num_vendas']:,}** registros"
    + (f" de {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}" if start_date and end_date else "")
)
st.divider()

# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    kpi_card("💰", "Receita Total", fmt_brl(kpis["receita_total"]))
with col2:
    kpi_card("🛒", "Número de Vendas", f"{kpis['num_vendas']:,}")
with col3:
    kpi_card("📊", "Ticket Médio", fmt_brl(kpis["ticket_medio"]))
with col4:
    kpi_card("✅", "Taxa de Aprovação", f"{kpis['taxa_aprovacao']:.1f}%")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Gráfico: Receita por Período (largura total)
# ---------------------------------------------------------------------------
st.plotly_chart(
    chart_receita_por_periodo(df_filtered, agrupamento),
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Gráficos: Produtos e Status
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.plotly_chart(
        chart_vendas_por_produto(df_filtered, top_n),
        use_container_width=True,
    )

with col_right:
    st.plotly_chart(
        chart_distribuicao_status(df_filtered),
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Gráfico: Método de pagamento
# ---------------------------------------------------------------------------
col_pay, col_empty = st.columns([1, 1])
with col_pay:
    st.plotly_chart(
        chart_metodo_pagamento(df_filtered),
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Seção: Análise de Origem / UTM
# ---------------------------------------------------------------------------
UTM_CAMPOS = [
    ("origem_3",    "Origem 3"),
    ("utm_source",  "UTM Source"),
    ("utm_campaign","UTM Campaign"),
    ("utm_medium",  "UTM Medium"),
    ("utm_content", "UTM Content"),
]

campos_presentes = [(campo, label) for campo, label in UTM_CAMPOS if campo in df_filtered.columns]

if campos_presentes:
    st.divider()
    st.subheader("Análise de Origem / UTM")

    for i in range(0, len(campos_presentes), 2):
        cols = st.columns(2)
        for j, (campo, label) in enumerate(campos_presentes[i:i+2]):
            with cols[j]:
                st.plotly_chart(
                    chart_receita_por_campo(df_filtered, campo, label),
                    use_container_width=True,
                )

# ---------------------------------------------------------------------------
# Tabela de Transações
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Transações Detalhadas")

display_cols = [c for c in ["data", "codigo", "contato", "produto", "valor", "metodo_pagamento", "status", "origem_3", "utm_source", "utm_campaign", "utm_medium", "utm_content"] if c in df_filtered.columns]
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
    df_display["valor"] = df_display["valor"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

df_display = df_display.rename(columns=col_labels)

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
    height=400,
)

st.caption(f"Total de {len(df_filtered):,} registros exibidos.")
