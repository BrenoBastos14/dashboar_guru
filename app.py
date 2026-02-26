import traceback

import pandas as pd
import streamlit as st

from utils.data_processor import clean_data, compute_kpis, filter_data, load_csv


# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Guru Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _brl(v):
    """Formata float como moeda BRL. Ex: 1234.5 → 'R$ 1.234,50'"""
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def _cell_style(val, vmax):
    """CSS de fundo proporcional ao valor — sem precisar de matplotlib."""
    if vmax == 0 or val == 0:
        return "background-color: #f5f5f5; color: #cccccc"
    intensity = float(val) / float(vmax)
    r = int(255 - (255 - 45)  * intensity)
    g = int(255 - (255 - 125) * intensity)
    b = int(255 - (255 - 70)  * intensity)
    text = "white" if intensity > 0.55 else "#222222"
    return f"background-color: rgb({r},{g},{b}); color: {text}"


def _resumo_tabela(df, campo, label):
    """Retorna DataFrame agrupado por campo com Vendas e Receita (R$)."""
    grp = df[df[campo].notna()].groupby(campo)["valor"]
    tbl = pd.concat(
        [grp.count().rename("Vendas"), grp.sum().rename("Receita (R$)")],
        axis=1,
    ).sort_values("Receita (R$)", ascending=False).reset_index()
    tbl["Receita (R$)"] = tbl["Receita (R$)"].apply(_brl)
    return tbl.rename(columns={campo: label})


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
    st.code(traceback.format_exc(), language="python")
    st.stop()

if df.empty:
    st.warning("O arquivo CSV está vazio ou não contém dados válidos.")
    st.stop()

# Diagnóstico — expander mostrando o que foi detectado
with st.expander("🔍 Diagnóstico — colunas detectadas no CSV", expanded=False):
    st.write(f"**Linhas carregadas:** {len(df):,}")
    st.write(f"**Colunas detectadas:** {list(df.columns)}")
    st.write(f"**`valor` presente:** {'Sim ✅' if 'valor' in df.columns else 'Não ❌'}")
    if "valor" in df.columns:
        st.write(f"**Amostra de valores:** {df['valor'].head(5).tolist()}")
    st.dataframe(df_raw.head(3), use_container_width=True)

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

    # ------------------------------------------------------------------
    # Facebook Ads — credenciais
    # ------------------------------------------------------------------
    st.divider()
    with st.expander("🔵 Facebook Ads (opcional)"):
        st.caption(
            "Preencha para cruzar seu gasto em anúncios com as vendas do Guru. "
            "Necessário um token com permissão **ads_read**."
        )
        fb_token = st.text_input("Access Token", type="password", key="fb_token")
        fb_account = st.text_input(
            "Ad Account ID",
            placeholder="Ex: 123456789",
            key="fb_account",
        )
        fb_ativo = bool(fb_token and fb_account)

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
# Header + KPIs
# ---------------------------------------------------------------------------
st.markdown("## 📊 Dashboard de Vendas — Guru Manager")

kpis = compute_kpis(df_filtered)

k1, k2, k3 = st.columns(3)
k1.metric("Volume de Vendas", f"{kpis['num_vendas']:,}")
k2.metric("Receita Total", _brl(kpis["receita_total"]))
k3.metric("Ticket Médio", _brl(kpis["ticket_medio"]))

st.divider()

# ---------------------------------------------------------------------------
# Resumo por Produto
# ---------------------------------------------------------------------------
if "produto" in df_filtered.columns and "valor" in df_filtered.columns:
    st.subheader("Resumo por Produto")
    tbl_produto = _resumo_tabela(df_filtered, "produto", "Produto")
    st.dataframe(tbl_produto, use_container_width=True, hide_index=True)
    st.divider()

# ---------------------------------------------------------------------------
# Resumo por Origem / UTM
# ---------------------------------------------------------------------------
_utm_resumo = [
    ("origem_3",    "Origem 3"),
    ("utm_source",  "UTM Source"),
    ("utm_campaign","UTM Campaign"),
    ("utm_medium",  "UTM Medium"),
    ("utm_content", "UTM Content"),
]
campos_resumo = [
    (c, l) for c, l in _utm_resumo
    if c in df_filtered.columns and "valor" in df_filtered.columns
]

if campos_resumo:
    st.subheader("Resumo por Origem / UTM")
    for i in range(0, len(campos_resumo), 2):
        cols = st.columns(2)
        for j, (campo, label) in enumerate(campos_resumo[i:i+2]):
            with cols[j]:
                st.markdown(f"**{label}**")
                st.dataframe(
                    _resumo_tabela(df_filtered, campo, label),
                    use_container_width=True,
                    hide_index=True,
                )
    st.divider()

# ---------------------------------------------------------------------------
# Pivot: Vendas por Dia × Origem / UTM
# ---------------------------------------------------------------------------
_pivot_campos = [
    ("origem_3",    "Origem 3"),
    ("utm_source",  "UTM Source"),
    ("utm_campaign","UTM Campaign"),
    ("utm_medium",  "UTM Medium"),
    ("utm_content", "UTM Content"),
]
campos_pivot = [
    (c, l) for c, l in _pivot_campos
    if c in df_filtered.columns
    and df_filtered[c].notna().any()
    and "valor" in df_filtered.columns
    and "data" in df_filtered.columns
]

if campos_pivot:
    st.subheader("Distribuição por Dia")
    metrica_pv = st.radio(
        "Métrica",
        ["Nº de Vendas", "Receita (R$)"],
        horizontal=True,
        key="radio_pivot",
    )
    use_count = metrica_pv == "Nº de Vendas"
    has_status = "status" in df_filtered.columns

    for campo, label in campos_pivot:
        df_tmp = df_filtered[df_filtered[campo].notna()].copy()
        df_tmp["_dia"] = df_tmp["data"].dt.date

        # Índice: campo + status (quando disponível)
        idx = [campo, "status"] if has_status else [campo]

        pivot = df_tmp.pivot_table(
            index=idx,
            columns="_dia",
            values="valor",
            aggfunc="count" if use_count else "sum",
            fill_value=0,
        )
        # Ordena colunas por data e formata como DD/MM
        pivot = pivot.sort_index(axis=1)
        pivot.columns = [pd.Timestamp(d).strftime("%d/%m") for d in pivot.columns]
        pivot.index.names = [label, "Status"] if has_status else [label]

        # Ordena primeiro nível pelo total decrescente
        if has_status:
            level0_order = (
                pivot.groupby(level=0).sum().sum(axis=1)
                .sort_values(ascending=False).index
            )
            pivot = pivot.loc[level0_order]
        else:
            pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

        if use_count:
            pivot = pivot.astype(int)
        vmax = float(pivot.values.max()) if pivot.values.max() > 0 else 1.0
        styled = pivot.style.applymap(lambda v: _cell_style(v, vmax))
        if use_count:
            styled = styled.format("{:d}")
        else:
            styled = styled.format(lambda v: _brl(v) if v > 0 else "—")

        with st.expander(f"**{label}**", expanded=True):
            st.dataframe(styled, use_container_width=True)

    st.divider()

# ---------------------------------------------------------------------------
# Facebook Ads — Desempenho por Campanha
# ---------------------------------------------------------------------------
if fb_ativo and start_date and end_date:
    from utils.facebook_ads import fetch_campaign_insights

    st.subheader("🔵 Facebook Ads — Desempenho por Campanha")

    @st.cache_data(ttl=300, show_spinner="Buscando dados do Facebook Ads…")
    def _buscar_fb(token, account, since, until):
        return fetch_campaign_insights(token, account, since, until)

    try:
        df_fb = _buscar_fb(
            fb_token,
            fb_account,
            str(start_date),
            str(end_date),
        )

        if df_fb.empty:
            st.info("Nenhuma campanha encontrada no Facebook Ads para o período selecionado.")
        else:
            # Agrupamento das vendas Guru por utm_campaign
            if "utm_campaign" in df_filtered.columns:
                df_guru_grp = (
                    df_filtered[df_filtered["utm_campaign"].notna()]
                    .groupby("utm_campaign")
                    .agg(vendas=("valor", "count"), receita=("valor", "sum"))
                    .reset_index()
                )
                df_guru_grp["_key"] = df_guru_grp["utm_campaign"].str.strip().str.lower()
            else:
                df_guru_grp = pd.DataFrame(columns=["_key", "vendas", "receita"])

            df_fb["_key"] = df_fb["campaign_name"].str.strip().str.lower()
            df_merged = df_fb.merge(df_guru_grp, on="_key", how="left")

            # Garante dtype numérico após o merge
            for _col in ["spend", "impressions", "clicks", "receita", "vendas"]:
                if _col in df_merged.columns:
                    df_merged[_col] = pd.to_numeric(df_merged[_col], errors="coerce").fillna(0)

            # Métricas combinadas (.where mantém dtype float, evita conversão para object)
            df_merged["ROAS"] = (
                df_merged["receita"] / df_merged["spend"].where(df_merged["spend"] > 0)
            ).round(2)
            df_merged["CPA (R$)"] = (
                df_merged["spend"] / df_merged["vendas"].where(df_merged["vendas"] > 0)
            ).round(2)
            df_merged["Conv. (%)"] = (
                df_merged["vendas"] / df_merged["clicks"].where(df_merged["clicks"] > 0) * 100
            ).round(2)

            # KPIs do Facebook
            fk1, fk2, fk3, fk4 = st.columns(4)
            fk1.metric("Total Gasto", _brl(df_merged["spend"].sum()))
            fk2.metric("Impressões", f"{int(df_merged['impressions'].sum()):,}")
            fk3.metric("Cliques", f"{int(df_merged['clicks'].sum()):,}")
            roas_total = (
                df_merged["receita"].sum() / df_merged["spend"].sum()
                if df_merged["spend"].sum() > 0 else 0
            )
            fk4.metric("ROAS Geral", f"{roas_total:.2f}x")

            st.markdown("")

            # Tabela por campanha
            exibir = df_merged.rename(columns={
                "campaign_name": "Campanha",
                "spend": "Gasto (R$)",
                "impressions": "Impressões",
                "clicks": "Cliques",
                "ctr": "CTR (%)",
                "reach": "Alcance",
                "vendas": "Vendas",
                "receita": "Receita (R$)",
            })
            colunas_exibir = [
                c for c in [
                    "Campanha", "Gasto (R$)", "Impressões", "Cliques", "CTR (%)",
                    "Alcance", "Vendas", "Receita (R$)", "ROAS", "CPA (R$)", "Conv. (%)",
                ] if c in exibir.columns
            ]
            exibir = (
                exibir[colunas_exibir]
                .sort_values("Receita (R$)", ascending=False, na_position="last")
                .reset_index(drop=True)
            )

            # Formata colunas monetárias
            fmt_brl = ["Gasto (R$)", "Receita (R$)", "CPA (R$)"]
            fmt_int = ["Impressões", "Cliques", "Alcance", "Vendas"]
            styled_fb = exibir.style
            for col in fmt_brl:
                if col in exibir.columns:
                    styled_fb = styled_fb.format(
                        lambda v, c=col: _brl(v) if pd.notna(v) else "—", subset=col
                    )
            for col in fmt_int:
                if col in exibir.columns:
                    styled_fb = styled_fb.format(
                        lambda v, c=col: f"{int(v):,}" if pd.notna(v) else "—", subset=col
                    )
            for col in ["CTR (%)", "Conv. (%)"]:
                if col in exibir.columns:
                    styled_fb = styled_fb.format(
                        lambda v: f"{v:.2f}%" if pd.notna(v) else "—", subset=col
                    )
            if "ROAS" in exibir.columns:
                styled_fb = styled_fb.format(
                    lambda v: f"{v:.2f}x" if pd.notna(v) else "—", subset="ROAS"
                )

            st.dataframe(styled_fb, use_container_width=True, hide_index=True)

            st.caption(
                "💡 O cruzamento é feito pelo nome da campanha no Facebook × coluna "
                "**utm_campaign** do CSV. Certifique-se de que os nomes coincidem."
            )

    except Exception as e:
        st.error(f"Erro ao buscar dados do Facebook Ads: {e}")

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
    df_display["valor"] = df_display["valor"].apply(_brl)

df_display = df_display.rename(columns=col_labels)

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
    height=600,
)

st.caption(f"Total de {len(df_filtered):,} registros exibidos.")
