import traceback

import pandas as pd
import streamlit as st

from utils.charts import (
    chart_receita_por_periodo,
    chart_fb_gasto_tempo,
    chart_fb_roas_campanhas,
    chart_fb_funil,
    chart_fb_scatter_eficiencia,
    chart_fb_spend_vs_receita,
    chart_fb_ctr_por_campanha,
)
from utils.data_processor import clean_data, compute_kpis, filter_data, load_csv
from utils.facebook_ads import (
    fetch_campaign_insights,
    fetch_campaign_insights_daily,
    parse_insights_to_df,
    parse_daily_insights_to_df,
    enrich_with_sales,
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

    # ------------------------------------------------------------------
    # Facebook Ads — credenciais
    # ------------------------------------------------------------------
    with st.expander("🔵 Facebook Ads (opcional)", expanded=False):
        fb_token = st.text_input(
            "Access Token",
            type="password",
            placeholder="EAAxxxxxx...",
            help="Token de acesso da Meta Marketing API.",
        )
        fb_account_id = st.text_input(
            "Ad Account ID",
            placeholder="act_123456789  ou  123456789",
            help="ID da conta de anúncios (com ou sem prefixo 'act_').",
        )
        fb_date_preset = st.selectbox(
            "Período",
            options=["last_7d", "last_30d", "this_month", "last_month"],
            format_func=lambda x: {
                "last_7d": "Últimos 7 dias",
                "last_30d": "Últimos 30 dias",
                "this_month": "Este mês",
                "last_month": "Mês passado",
            }[x],
        )
        fb_connect = st.button("Conectar Facebook Ads", type="primary")

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
    st.markdown("**Período**")
    if "data" in df.columns:
        min_date = df["data"].min().date()
        max_date = df["data"].max().date()
        start_date = st.date_input("Data inicial", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("Data final", value=max_date, min_value=min_date, max_value=max_date)
    else:
        st.caption("Coluna de data não detectada no CSV.")
        start_date = end_date = None

    st.divider()
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

    # Agrupamento temporal
    if "data" in df.columns:
        st.divider()
        agrupamento = st.radio(
            "Agrupar receita por",
            options=["D", "W", "ME"],
            format_func=lambda x: {"D": "Dia", "W": "Semana", "ME": "Mês"}[x],
            horizontal=True,
            index=0,
        )
    else:
        agrupamento = "D"


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
# Gráfico: Receita por Período
# ---------------------------------------------------------------------------
st.plotly_chart(
    chart_receita_por_periodo(df_filtered, agrupamento),
    use_container_width=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Status por Dia
# ---------------------------------------------------------------------------
if (
    "status" in df_filtered.columns
    and "data" in df_filtered.columns
    and "valor" in df_filtered.columns
    and not df_filtered.empty
):
    st.subheader("Status por Dia")
    metrica_st = st.radio(
        "Métrica",
        ["Nº de Vendas", "Receita (R$)"],
        horizontal=True,
        key="radio_status_dia",
    )
    use_count_st = metrica_st == "Nº de Vendas"

    df_st = df_filtered.copy()
    df_st["_dia"] = df_st["data"].dt.date

    pivot_st = df_st.pivot_table(
        index="status",
        columns="_dia",
        values="valor",
        aggfunc="count" if use_count_st else "sum",
        fill_value=0,
    )
    pivot_st = pivot_st.sort_index(axis=1)
    pivot_st.columns = [pd.Timestamp(d).strftime("%d/%m") for d in pivot_st.columns]
    pivot_st.index.name = "Status"

    # Ordena por total decrescente
    pivot_st = pivot_st.loc[pivot_st.sum(axis=1).sort_values(ascending=False).index]

    if use_count_st:
        pivot_st = pivot_st.astype(int)
    vmax_st = float(pivot_st.values.max()) if pivot_st.values.max() > 0 else 1.0
    styled_st = pivot_st.style.applymap(lambda v: _cell_style(v, vmax_st))
    if use_count_st:
        styled_st = styled_st.format("{:d}")
    else:
        styled_st = styled_st.format(lambda v: _brl(v) if v > 0 else "—")

    st.dataframe(styled_st, use_container_width=True)
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
# Facebook Ads — Análise de Métricas
# ---------------------------------------------------------------------------
if fb_connect and fb_token and fb_account_id:
    st.markdown("## 🔵 Facebook Ads — Análise de Métricas")

    with st.spinner("Carregando dados do Facebook Ads..."):
        try:
            raw_rows = fetch_campaign_insights(fb_token, fb_account_id, fb_date_preset)
            raw_daily = fetch_campaign_insights_daily(fb_token, fb_account_id, fb_date_preset)
            df_fb = parse_insights_to_df(raw_rows)
            df_daily = parse_daily_insights_to_df(raw_daily)
            fb_error = None
        except Exception as exc:
            df_fb = pd.DataFrame()
            df_daily = pd.DataFrame()
            fb_error = str(exc)

    if fb_error:
        st.error(f"Erro ao conectar ao Facebook Ads: {fb_error}")
    elif df_fb.empty:
        st.info("Nenhuma campanha encontrada para o período selecionado.")
    else:
        # Cruza com dados de vendas do CSV
        df_camp = enrich_with_sales(df_fb, df_filtered)

        # Métricas globais
        total_spend      = df_camp["spend"].sum()
        total_impressions = int(df_camp["impressions"].sum()) if "impressions" in df_camp.columns else 0
        total_reach      = int(df_camp["reach"].sum()) if "reach" in df_camp.columns else 0
        total_clicks     = int(df_camp["clicks"].sum()) if "clicks" in df_camp.columns else 0
        total_vendas_fb  = int(df_camp["vendas"].sum())
        receita_total_fb = df_camp["receita"].sum()
        roas_global      = receita_total_fb / total_spend if total_spend > 0 else 0
        ctr_medio        = df_camp["ctr"].mean() if "ctr" in df_camp.columns else 0
        cpc_medio        = (
            total_spend / total_clicks if total_clicks > 0 else 0
        )
        cpa_global       = total_spend / total_vendas_fb if total_vendas_fb > 0 else 0

        # ── Tabs ────────────────────────────────────────────────────────────
        tab_geral, tab_campanhas, tab_cruzamento = st.tabs([
            "📊 Visão Geral",
            "📋 Campanhas",
            "🔗 Cruzamento com Vendas",
        ])

        # ── TAB 1: Visão Geral ───────────────────────────────────────────────
        with tab_geral:
            # KPI cards — linha 1
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Gasto Total",    _brl(total_spend))
            c2.metric("Impressões",     f"{total_impressions:,}")
            c3.metric("Alcance",        f"{total_reach:,}")
            c4.metric("Cliques",        f"{total_clicks:,}")
            c5.metric("CTR Médio",      f"{ctr_medio:.2f}%")

            # KPI cards — linha 2
            d1, d2, d3, d4, d5 = st.columns(5)
            d1.metric("CPC Médio",      _brl(cpc_medio))
            d2.metric("Vendas (CSV)",   f"{total_vendas_fb:,}")
            d3.metric("Receita (CSV)",  _brl(receita_total_fb))
            d4.metric("ROAS Global",    f"{roas_global:.2f}×")
            d5.metric("CPA Global",     _brl(cpa_global))

            st.divider()

            # Funil + Gasto diário
            col_funil, col_gasto = st.columns([1, 2])
            with col_funil:
                st.plotly_chart(
                    chart_fb_funil(
                        total_impressions, total_reach, total_clicks, total_vendas_fb
                    ),
                    use_container_width=True,
                )
            with col_gasto:
                st.plotly_chart(
                    chart_fb_gasto_tempo(df_daily),
                    use_container_width=True,
                )

        # ── TAB 2: Campanhas ─────────────────────────────────────────────────
        with tab_campanhas:
            # Filtro de campanha
            camp_opts = sorted(df_camp["campaign_name"].dropna().unique().tolist())
            camp_sel = st.multiselect(
                "Filtrar campanhas",
                options=camp_opts,
                default=camp_opts,
                key="fb_camp_filter",
            )
            df_camp_fil = df_camp[df_camp["campaign_name"].isin(camp_sel)] if camp_sel else df_camp

            # Gráficos
            col_roas, col_ctr = st.columns(2)
            with col_roas:
                st.plotly_chart(
                    chart_fb_roas_campanhas(df_camp_fil),
                    use_container_width=True,
                )
            with col_ctr:
                st.plotly_chart(
                    chart_fb_ctr_por_campanha(df_camp_fil),
                    use_container_width=True,
                )

            st.plotly_chart(
                chart_fb_scatter_eficiencia(df_camp_fil),
                use_container_width=True,
            )

            st.subheader("Tabela de Campanhas")
            _disp_cols = [c for c in [
                "campaign_name", "spend", "impressions", "clicks", "ctr",
                "cpc", "reach", "frequency", "vendas", "receita", "ROAS", "CPA", "conv_rate",
            ] if c in df_camp_fil.columns]
            _rename = {
                "campaign_name": "Campanha",
                "spend":         "Gasto (R$)",
                "impressions":   "Impressões",
                "clicks":        "Cliques",
                "ctr":           "CTR (%)",
                "cpc":           "CPC (R$)",
                "reach":         "Alcance",
                "frequency":     "Freq.",
                "vendas":        "Vendas",
                "receita":       "Receita (R$)",
                "ROAS":          "ROAS",
                "CPA":           "CPA (R$)",
                "conv_rate":     "Conv. (%)",
            }
            disp = df_camp_fil[_disp_cols].rename(columns=_rename).copy()

            for col in ["Gasto (R$)", "CPC (R$)", "Receita (R$)", "CPA (R$)"]:
                if col in disp.columns:
                    disp[col] = disp[col].apply(_brl)
            for col in ["CTR (%)", "Conv. (%)"]:
                if col in disp.columns:
                    disp[col] = disp[col].apply(lambda v: f"{v:.2f}%")
            if "ROAS" in disp.columns:
                disp["ROAS"] = disp["ROAS"].apply(lambda v: f"{v:.2f}×")
            if "Freq." in disp.columns:
                disp["Freq."] = disp["Freq."].apply(lambda v: f"{v:.1f}")

            st.dataframe(disp, use_container_width=True, hide_index=True)

        # ── TAB 3: Cruzamento com Vendas ─────────────────────────────────────
        with tab_cruzamento:
            has_sales_data = df_camp["receita"].sum() > 0

            if not has_sales_data:
                st.info(
                    "Nenhuma receita cruzada encontrada. "
                    "Verifique se o CSV contém a coluna **utm_campaign** "
                    "com nomes correspondentes às campanhas do Facebook."
                )
            else:
                # Gráfico Gasto vs Receita
                st.plotly_chart(
                    chart_fb_spend_vs_receita(df_camp),
                    use_container_width=True,
                )

                st.divider()

                # Ranking por ROAS
                st.subheader("Ranking por ROAS")
                df_rank = df_camp[df_camp["ROAS"] > 0].sort_values("ROAS", ascending=False).copy()
                df_rank["Rentável?"] = df_rank["ROAS"].apply(lambda v: "✅ Sim" if v >= 1 else "❌ Não")

                rank_cols = ["campaign_name", "spend", "receita", "ROAS", "CPA", "conv_rate", "vendas", "Rentável?"]
                rank_cols = [c for c in rank_cols if c in df_rank.columns]
                rank_disp = df_rank[rank_cols].rename(columns={
                    "campaign_name": "Campanha",
                    "spend":         "Gasto (R$)",
                    "receita":       "Receita (R$)",
                    "ROAS":          "ROAS",
                    "CPA":           "CPA (R$)",
                    "conv_rate":     "Conv. (%)",
                    "vendas":        "Vendas",
                }).copy()

                for col in ["Gasto (R$)", "Receita (R$)", "CPA (R$)"]:
                    if col in rank_disp.columns:
                        rank_disp[col] = rank_disp[col].apply(_brl)
                if "ROAS" in rank_disp.columns:
                    rank_disp["ROAS"] = rank_disp["ROAS"].apply(lambda v: f"{v:.2f}×")
                if "Conv. (%)" in rank_disp.columns:
                    rank_disp["Conv. (%)"] = rank_disp["Conv. (%)"].apply(lambda v: f"{v:.2f}%")

                st.dataframe(rank_disp, use_container_width=True, hide_index=True)

                # Resumo de campanhas rentáveis vs não-rentáveis
                st.divider()
                rentaveis    = (df_camp["ROAS"] >= 1).sum()
                nao_rentaveis = (df_camp["ROAS"] > 0) & (df_camp["ROAS"] < 1)
                nao_rentaveis = nao_rentaveis.sum()
                sem_dados    = (df_camp["ROAS"] == 0).sum()

                r1, r2, r3 = st.columns(3)
                r1.metric("Campanhas Rentáveis (ROAS ≥ 1)",    f"{rentaveis}")
                r2.metric("Campanhas com ROAS < 1",            f"{nao_rentaveis}")
                r3.metric("Campanhas sem dados de receita",    f"{sem_dados}")

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
