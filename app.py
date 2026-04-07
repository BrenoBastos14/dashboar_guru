import traceback

import pandas as pd
import streamlit as st

from utils.charts import chart_receita_por_periodo
from utils.data_processor import clean_data, compute_kpis, filter_data, load_csv
from utils.facebook_data import (
    aggregate_fb_metrics,
    load_facebook_file,
    merge_fb_guru,
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


def _cell_style_red(val, vmax):
    """CSS heatmap vermelho (para gasto)."""
    if vmax == 0 or val == 0:
        return "background-color: #f5f5f5; color: #cccccc"
    intensity = float(val) / float(vmax)
    r = int(255 - (255 - 220) * intensity)
    g = int(255 - (255 - 38)  * intensity)
    b = int(255 - (255 - 38)  * intensity)
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
        "Carregar CSV ou Excel (Guru)",
        type=["csv", "xlsx"],
        help="Exporte o relatório de vendas no Guru Manager e faça upload aqui (.csv ou .xlsx).",
    )

    uploaded_fb = st.file_uploader(
        "Carregar CSV ou Excel (Facebook Ads)",
        type=["csv", "xlsx"],
        help="Exporte o relatório de gastos do Facebook Ads e faça upload aqui.",
    )

    st.divider()
    st.subheader("Filtros")

# ---------------------------------------------------------------------------
# Tabs principais
# ---------------------------------------------------------------------------
tab_guru, tab_fb = st.tabs(["📊 Vendas Guru Manager", "📱 Facebook Ads"])

# ===========================================================================
# TAB 1 — Guru Manager
# ===========================================================================
with tab_guru:
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

    # -----------------------------------------------------------------------
    # Carrega e processa dados
    # -----------------------------------------------------------------------
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

    # Diagnóstico
    with st.expander("🔍 Diagnóstico — colunas detectadas no CSV", expanded=False):
        st.write(f"**Linhas carregadas:** {len(df):,}")
        st.write(f"**Colunas detectadas:** {list(df.columns)}")
        st.write(f"**`valor` presente:** {'Sim ✅' if 'valor' in df.columns else 'Não ❌'}")
        if "valor" in df.columns:
            st.write(f"**Amostra de valores:** {df['valor'].head(5).tolist()}")
        st.dataframe(df_raw.head(3), use_container_width=True)

    # -----------------------------------------------------------------------
    # Filtros na sidebar
    # -----------------------------------------------------------------------
    with st.sidebar:
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
        status_opts = sorted(df["status"].dropna().unique().tolist()) if "status" in df.columns else []
        selected_status = st.multiselect("Status", options=status_opts, default=status_opts)

        produto_opts = sorted(df["produto"].dropna().unique().tolist()) if "produto" in df.columns else []
        selected_produtos = st.multiselect("Produto", options=produto_opts, default=produto_opts)

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

    # -----------------------------------------------------------------------
    # Aplica filtros
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # Header + KPIs
    # -----------------------------------------------------------------------
    st.markdown("## 📊 Dashboard de Vendas — Guru Manager")

    kpis = compute_kpis(df_filtered)

    k1, k2, k3 = st.columns(3)
    k1.metric("Volume de Vendas", f"{kpis['num_vendas']:,}")
    k2.metric("Receita Total", _brl(kpis["receita_total"]))
    k3.metric("Ticket Médio", _brl(kpis["ticket_medio"]))

    st.divider()

    # -----------------------------------------------------------------------
    # Gráfico: Receita por Período
    # -----------------------------------------------------------------------
    st.plotly_chart(
        chart_receita_por_periodo(df_filtered, agrupamento),
        use_container_width=True,
    )

    st.divider()

    # -----------------------------------------------------------------------
    # Status por Dia
    # -----------------------------------------------------------------------
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

        pivot_st = pivot_st.loc[pivot_st.sum(axis=1).sort_values(ascending=False).index]

        if use_count_st:
            pivot_st = pivot_st.astype(int)
        vmax_st = float(pivot_st.values.max()) if pivot_st.values.max() > 0 else 1.0
        styled_st = pivot_st.style.map(lambda v: _cell_style(v, vmax_st))
        if use_count_st:
            styled_st = styled_st.format("{:d}")
        else:
            styled_st = styled_st.format(lambda v: _brl(v) if v > 0 else "—")

        st.dataframe(styled_st, use_container_width=True)
        st.divider()

    # -----------------------------------------------------------------------
    # Resumo por Produto
    # -----------------------------------------------------------------------
    if "produto" in df_filtered.columns and "valor" in df_filtered.columns:
        st.subheader("Resumo por Produto")
        tbl_produto = _resumo_tabela(df_filtered, "produto", "Produto")
        st.dataframe(tbl_produto, use_container_width=True, hide_index=True)
        st.divider()

    # -----------------------------------------------------------------------
    # Resumo por Origem / UTM
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # Pivot: Vendas por Dia × Origem / UTM
    # -----------------------------------------------------------------------
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

            idx = [campo, "status"] if has_status else [campo]

            pivot = df_tmp.pivot_table(
                index=idx,
                columns="_dia",
                values="valor",
                aggfunc="count" if use_count else "sum",
                fill_value=0,
            )
            pivot = pivot.sort_index(axis=1)
            pivot.columns = [pd.Timestamp(d).strftime("%d/%m") for d in pivot.columns]
            pivot.index.names = [label, "Status"] if has_status else [label]

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
            styled = pivot.style.map(lambda v: _cell_style(v, vmax))
            if use_count:
                styled = styled.format("{:d}")
            else:
                styled = styled.format(lambda v: _brl(v) if v > 0 else "—")

            with st.expander(f"**{label}**", expanded=True):
                st.dataframe(styled, use_container_width=True)

        st.divider()

    # -----------------------------------------------------------------------
    # Tabela de Transações
    # -----------------------------------------------------------------------
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


# ===========================================================================
# TAB 2 — Facebook Ads
# ===========================================================================
with tab_fb:
    st.markdown("## 📱 Facebook Ads — Análise de Gastos e ROAS")

    if uploaded_fb is None:
        st.info(
            "**Faça upload do relatório de gastos do Facebook Ads** usando o painel lateral.\n\n"
            "**Como exportar?**\n"
            "1. Acesse o **Gerenciador de Anúncios** do Facebook\n"
            "2. Vá em **Relatórios → Relatório Personalizado**\n"
            "3. Adicione as colunas: *Nome da campanha, Nome do conjunto, Nome do anúncio, "
            "Hora do dia, Valor usado (BRL), Início dos relatórios*\n"
            "4. Exporte como CSV ou Excel\n"
            "5. Faça upload aqui",
            icon="💡",
        )
        if uploaded_file is None:
            st.warning("Faça também o upload do arquivo de vendas do Guru Manager para cruzar os dados.")
        st.stop()

    # -----------------------------------------------------------------------
    # Carrega arquivo FB
    # -----------------------------------------------------------------------
    try:
        df_fb = load_facebook_file(uploaded_fb)
    except Exception as e:
        st.error(f"Erro ao processar o arquivo do Facebook Ads: {e}")
        st.code(traceback.format_exc(), language="python")
        st.stop()

    if df_fb.empty:
        st.warning("O arquivo do Facebook Ads está vazio ou não contém dados válidos.")
        st.stop()

    with st.expander("🔍 Diagnóstico — colunas detectadas (Facebook Ads)", expanded=False):
        st.write(f"**Linhas carregadas:** {len(df_fb):,}")
        st.write(f"**Colunas detectadas:** {list(df_fb.columns)}")
        hora_ok = "hora" in df_fb.columns and df_fb["hora"].notna().any()
        st.write(f"**`hora` detectada:** {'Sim ✅' if hora_ok else 'Não ❌ — coluna Hora do dia não encontrada no arquivo'}")
        if hora_ok:
            st.write(f"**Amostra de horas:** {df_fb['hora'].dropna().unique()[:10].tolist()}")
        st.write(f"**`gasto` detectado:** {'Sim ✅' if 'gasto' in df_fb.columns else 'Não ❌'}")
        if "gasto" in df_fb.columns:
            st.write(f"**Amostra de gastos:** {df_fb['gasto'].head(5).tolist()}")
        st.dataframe(df_fb.head(5), use_container_width=True)

    # -----------------------------------------------------------------------
    # KPIs Facebook
    # -----------------------------------------------------------------------
    total_gasto = df_fb["gasto"].sum() if "gasto" in df_fb.columns else 0.0
    fb_k1, fb_k2, fb_k3 = st.columns(3)
    fb_k1.metric("Total Gasto (FB Ads)", _brl(total_gasto))

    # Cruzamento com Guru (se disponível)
    guru_available = uploaded_file is not None and "df_filtered" in dir()

    if guru_available and not df_filtered.empty:
        df_merged = merge_fb_guru(df_fb, df_filtered)
        total_receita_fb = df_merged["receita"].sum() if "receita" in df_merged.columns else 0.0
        total_vendas_fb = int(df_merged["vendas"].sum()) if "vendas" in df_merged.columns else 0
        roas_geral = total_receita_fb / total_gasto if total_gasto > 0 else 0.0
        cpa_geral = total_gasto / total_vendas_fb if total_vendas_fb > 0 else 0.0

        fb_k2.metric("Receita Atribuída (Guru)", _brl(total_receita_fb))
        fb_k3.metric("ROAS Geral", f"{roas_geral:.2f}x")

        m1, m2 = st.columns(2)
        m1.metric("Vendas Atribuídas", f"{total_vendas_fb:,}")
        m2.metric("CPA Médio", _brl(cpa_geral))

        st.divider()

        # -------------------------------------------------------------------
        # Tabelas por nível
        # -------------------------------------------------------------------
        nivel = st.radio(
            "Visualizar por",
            ["Campanha", "Conjunto de Anúncios", "Anúncio", "Hora do Dia"],
            horizontal=True,
        )

        nivel_map = {
            "Campanha": ["campanha"],
            "Conjunto de Anúncios": ["campanha", "conjunto"],
            "Anúncio": ["campanha", "conjunto", "anuncio"],
            "Hora do Dia": ["hora"],
        }
        group_cols = nivel_map[nivel]

        # Se "Hora do Dia" selecionado mas hora não foi detectada no arquivo, avisa
        hora_disponivel = "hora" in df_fb.columns and df_fb["hora"].notna().any()
        if nivel == "Hora do Dia" and not hora_disponivel:
            st.warning(
                "**Coluna de hora não encontrada no arquivo do Facebook Ads.**\n\n"
                "Para ver métricas por hora, exporte o relatório com a quebra **'Hora do dia'** "
                "ativada no Gerenciador de Anúncios.\n\n"
                "Abra o diagnóstico acima para ver quais colunas foram detectadas."
            )
        else:
            tbl = aggregate_fb_metrics(df_merged, group_cols)

            # Para "Hora do Dia", ordenar por hora (0-23) em vez de gasto
            if nivel == "Hora do Dia" and "hora" in tbl.columns:
                tbl = tbl.sort_values("hora").reset_index(drop=True)

            if tbl.empty:
                st.warning("Nenhum dado para exibir com o agrupamento selecionado.")
            else:
                label_map = {
                    "campanha": "Campanha",
                    "conjunto": "Conjunto",
                    "anuncio": "Anúncio",
                    "hora": "Hora do Dia",
                    "gasto": "Gasto (R$)",
                    "vendas": "Vendas",
                    "receita": "Receita (R$)",
                    "roas": "ROAS",
                    "cpa": "CPA (R$)",
                }
                tbl_display = tbl.copy()

                # Format monetary columns
                for col in ("gasto", "receita", "cpa"):
                    if col in tbl_display.columns:
                        tbl_display[col] = tbl_display[col].apply(_brl)

                if "roas" in tbl_display.columns:
                    tbl_display["roas"] = tbl_display["roas"].apply(lambda v: f"{v:.2f}x")

                if "hora" in tbl_display.columns:
                    tbl_display["hora"] = tbl_display["hora"].apply(
                        lambda v: f"{int(v):02d}:00 – {int(v):02d}:59" if pd.notna(v) else "—"
                    )

                tbl_display = tbl_display.rename(columns=label_map)
                st.dataframe(tbl_display, use_container_width=True, hide_index=True)

        st.divider()

        # -------------------------------------------------------------------
        # Pivot: Gasto por Campanha × Dia
        # -------------------------------------------------------------------
        if "campanha" in df_merged.columns and "_data" in df_merged.columns:
            st.subheader("Gasto por Campanha × Dia")
            df_pivot_fb = df_merged.copy()
            df_pivot_fb["_dia"] = pd.to_datetime(df_pivot_fb["_data"]).dt.strftime("%d/%m")

            pivot_fb = df_pivot_fb.pivot_table(
                index="campanha",
                columns="_dia",
                values="gasto",
                aggfunc="sum",
                fill_value=0,
            )
            pivot_fb.index.name = "Campanha"
            pivot_fb = pivot_fb.loc[pivot_fb.sum(axis=1).sort_values(ascending=False).index]

            vmax_fb = float(pivot_fb.values.max()) if pivot_fb.values.max() > 0 else 1.0
            styled_fb = pivot_fb.style.map(lambda v: _cell_style_red(v, vmax_fb))
            styled_fb = styled_fb.format(lambda v: _brl(v) if v > 0 else "—")
            st.dataframe(styled_fb, use_container_width=True)

    else:
        # No Guru data — show only FB metrics
        fb_k2.metric("Receita Atribuída", "—")
        fb_k3.metric("ROAS Geral", "—")

        if uploaded_file is None:
            st.warning(
                "Faça upload do arquivo de vendas do Guru Manager para cruzar os dados e calcular ROAS, CPA e conversão."
            )

        st.divider()
        st.subheader("Gastos por Campanha")

        if "campanha" in df_fb.columns and "gasto" in df_fb.columns:
            tbl_camp = (
                df_fb.groupby("campanha")["gasto"]
                .sum()
                .reset_index()
                .sort_values("gasto", ascending=False)
            )
            tbl_camp["gasto"] = tbl_camp["gasto"].apply(_brl)
            tbl_camp.columns = ["Campanha", "Gasto (R$)"]
            st.dataframe(tbl_camp, use_container_width=True, hide_index=True)

        if "conjunto" in df_fb.columns and "gasto" in df_fb.columns:
            st.subheader("Gastos por Conjunto de Anúncios")
            tbl_conj = (
                df_fb.groupby(["campanha", "conjunto"])["gasto"]
                .sum()
                .reset_index()
                .sort_values("gasto", ascending=False)
            )
            tbl_conj["gasto"] = tbl_conj["gasto"].apply(_brl)
            tbl_conj.columns = ["Campanha", "Conjunto", "Gasto (R$)"]
            st.dataframe(tbl_conj, use_container_width=True, hide_index=True)
