import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Paleta de cores consistente
COLORS_PRIMARY = [
    "#4F46E5",  # indigo
    "#7C3AED",  # violet
    "#DB2777",  # pink
    "#059669",  # emerald
    "#D97706",  # amber
    "#DC2626",  # red
    "#2563EB",  # blue
    "#0891B2",  # cyan
]

COLOR_APROVADO = "#059669"
COLOR_CANCELADO = "#DC2626"
COLOR_PENDENTE = "#D97706"
COLOR_REEMBOLSADO = "#7C3AED"
COLOR_DEFAULT = "#94A3B8"

STATUS_COLOR_MAP = {
    "Aprovado": COLOR_APROVADO,
    "Aprovada": COLOR_APROVADO,
    "Completa": COLOR_APROVADO,
    "Completo": COLOR_APROVADO,
    "Pago": COLOR_APROVADO,
    "Cancelado": COLOR_CANCELADO,
    "Cancelada": COLOR_CANCELADO,
    "Pendente": COLOR_PENDENTE,
    "Reembolsada": COLOR_REEMBOLSADO,
    "Reembolsado": COLOR_REEMBOLSADO,
    "Reclamada": "#F59E0B",
    "Reclamado": "#F59E0B",
}


def _format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def chart_receita_por_periodo(df: pd.DataFrame, agrupamento: str = "D") -> go.Figure:
    """
    Gráfico de linha: Receita por período.
    agrupamento: 'D' (dia), 'W' (semana), 'ME' (mês)
    """
    if "data" not in df.columns or "valor" not in df.columns or df.empty:
        return _empty_chart("Sem dados para o período selecionado")

    label_map = {"D": "Dia", "W": "Semana", "ME": "Mês"}

    series = (
        df.set_index("data")["valor"]
        .resample(agrupamento)
        .sum()
        .reset_index()
    )
    series.columns = ["data", "receita"]
    series["receita_fmt"] = series["receita"].apply(_format_brl)

    fig = px.line(
        series,
        x="data",
        y="receita",
        markers=True,
        labels={"data": "Data", "receita": "Receita (R$)"},
        color_discrete_sequence=[COLORS_PRIMARY[0]],
        custom_data=["receita_fmt"],
    )
    fig.update_traces(
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Receita: %{customdata[0]}<extra></extra>",
        line=dict(width=2.5),
        marker=dict(size=6),
    )
    fig.update_layout(
        title=f"Receita por {label_map.get(agrupamento, 'Período')}",
        xaxis_title=None,
        yaxis_title="R$",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#E2E8F0"),
        xaxis=dict(gridcolor="#E2E8F0"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_vendas_por_produto(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Gráfico de barras horizontal: Top N produtos por receita."""
    if "produto" not in df.columns or "valor" not in df.columns or df.empty:
        return _empty_chart("Sem dados de produto")

    top = (
        df.groupby("produto")["valor"]
        .sum()
        .nlargest(top_n)
        .reset_index()
        .sort_values("valor")
    )
    top["valor_fmt"] = top["valor"].apply(_format_brl)

    fig = px.bar(
        top,
        x="valor",
        y="produto",
        orientation="h",
        labels={"valor": "Receita (R$)", "produto": "Produto"},
        color_discrete_sequence=[COLORS_PRIMARY[0]],
        custom_data=["valor_fmt"],
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Receita: %{customdata[0]}<extra></extra>",
    )
    fig.update_layout(
        title=f"Top {top_n} Produtos por Receita",
        xaxis_title="R$",
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#E2E8F0"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_distribuicao_status(df: pd.DataFrame) -> go.Figure:
    """Gráfico de pizza: Distribuição por status."""
    if "status" not in df.columns or df.empty:
        return _empty_chart("Sem dados de status")

    counts = df["status"].value_counts().reset_index()
    counts.columns = ["status", "quantidade"]

    colors = [STATUS_COLOR_MAP.get(s, COLOR_DEFAULT) for s in counts["status"]]

    fig = px.pie(
        counts,
        names="status",
        values="quantidade",
        color="status",
        color_discrete_map=STATUS_COLOR_MAP,
        hole=0,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Porcentagem: %{percent}<extra></extra>",
        marker=dict(colors=colors),
    )
    fig.update_layout(
        title="Distribuição por Status",
        showlegend=True,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="v"),
    )
    return fig


def chart_metodo_pagamento(df: pd.DataFrame) -> go.Figure:
    """Gráfico de rosca: Métodos de pagamento."""
    if "metodo_pagamento" not in df.columns or df.empty:
        return _empty_chart("Sem dados de método de pagamento")

    counts = df["metodo_pagamento"].value_counts().reset_index()
    counts.columns = ["metodo", "quantidade"]

    fig = px.pie(
        counts,
        names="metodo",
        values="quantidade",
        hole=0.45,
        color_discrete_sequence=COLORS_PRIMARY,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Porcentagem: %{percent}<extra></extra>",
    )
    fig.update_layout(
        title="Método de Pagamento",
        showlegend=True,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_receita_por_campo(df: pd.DataFrame, campo: str, titulo: str, top_n: int = 10) -> go.Figure:
    """Gráfico de barras horizontal: Receita por campo (origem_3, utm_source, etc.)."""
    if campo not in df.columns or "valor" not in df.columns or df.empty:
        return _empty_chart(f"Sem dados de {titulo}")

    top = (
        df[df[campo].notna() & (df[campo].astype(str).str.strip() != "")]
        .groupby(campo)["valor"]
        .sum()
        .nlargest(top_n)
        .reset_index()
        .sort_values("valor")
    )

    if top.empty:
        return _empty_chart(f"Sem dados de {titulo}")

    top["valor_fmt"] = top["valor"].apply(_format_brl)
    top["quantidade"] = df.groupby(campo)["valor"].count().reindex(top[campo]).values

    fig = px.bar(
        top,
        x="valor",
        y=campo,
        orientation="h",
        labels={"valor": "Receita (R$)", campo: titulo},
        color_discrete_sequence=[COLORS_PRIMARY[0]],
        custom_data=["valor_fmt", "quantidade"],
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Receita: %{customdata[0]}<br>Vendas: %{customdata[1]}<extra></extra>",
    )
    fig.update_layout(
        title=f"Receita por {titulo}",
        xaxis_title="R$",
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#E2E8F0"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
# Facebook Ads — gráficos
# ---------------------------------------------------------------------------

def chart_fb_gasto_tempo(df_daily: "pd.DataFrame") -> "go.Figure":
    """Linha: gasto total diário ao longo do tempo."""
    if df_daily.empty or "date" not in df_daily.columns or "spend" not in df_daily.columns:
        return _empty_chart("Sem dados de gasto diário")

    series = df_daily.groupby("date")["spend"].sum().reset_index()
    series.columns = ["date", "spend"]
    series["spend_fmt"] = series["spend"].apply(_format_brl)

    fig = px.area(
        series,
        x="date",
        y="spend",
        labels={"date": "Data", "spend": "Gasto (R$)"},
        color_discrete_sequence=["#1877F2"],
        custom_data=["spend_fmt"],
    )
    fig.update_traces(
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Gasto: %{customdata[0]}<extra></extra>",
        line=dict(width=2.5),
        fillcolor="rgba(24,119,242,0.15)",
    )
    fig.update_layout(
        title="Gasto Diário",
        xaxis_title=None,
        yaxis_title="R$",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#E2E8F0"),
        xaxis=dict(gridcolor="#E2E8F0"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_fb_roas_campanhas(df_camp: "pd.DataFrame") -> "go.Figure":
    """Barra horizontal: ROAS por campanha, ordenado decrescente."""
    if df_camp.empty or "campaign_name" not in df_camp.columns or "ROAS" not in df_camp.columns:
        return _empty_chart("Sem dados de ROAS por campanha")

    df = df_camp[df_camp["ROAS"] > 0].sort_values("ROAS").tail(15)
    if df.empty:
        return _empty_chart("Nenhuma campanha com ROAS calculado")

    colors = ["#059669" if v >= 1 else "#DC2626" for v in df["ROAS"]]

    fig = go.Figure(go.Bar(
        x=df["ROAS"],
        y=df["campaign_name"],
        orientation="h",
        marker_color=colors,
        customdata=df[["spend", "receita"]].values if "spend" in df.columns and "receita" in df.columns else None,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "ROAS: %{x:.2f}×<br>"
            "Gasto: R$ %{customdata[0]:,.2f}<br>"
            "Receita: R$ %{customdata[1]:,.2f}<extra></extra>"
        ),
    ))
    fig.add_vline(x=1, line_dash="dash", line_color="#94A3B8", annotation_text="Break-even")
    fig.update_layout(
        title="ROAS por Campanha",
        xaxis_title="ROAS",
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#E2E8F0"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_fb_funil(total_impressions: int, total_reach: int, total_clicks: int, total_vendas: int) -> "go.Figure":
    """Funil: Impressões → Alcance → Cliques → Vendas."""
    labels = ["Impressões", "Alcance", "Cliques", "Vendas"]
    values = [total_impressions, total_reach, total_clicks, total_vendas]
    colors = ["#1877F2", "#42A5F5", "#0891B2", "#059669"]

    # Filtra estágios zerados (exceto Vendas que pode ser 0)
    pairs = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0 or l == "Vendas"]
    if not pairs:
        return _empty_chart("Sem dados para o funil")

    labels, values, colors = zip(*pairs) if pairs else ([], [], [])

    fig = go.Figure(go.Funnel(
        y=list(labels),
        x=list(values),
        textinfo="value+percent initial",
        marker=dict(color=list(colors)),
        hovertemplate="<b>%{y}</b><br>%{x:,}<extra></extra>",
    ))
    fig.update_layout(
        title="Funil de Conversão",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_fb_scatter_eficiencia(df_camp: "pd.DataFrame") -> "go.Figure":
    """Scatter: CTR (x) vs CPC (y) por campanha, tamanho = gasto, cor = ROAS."""
    needed = {"campaign_name", "ctr", "cpc", "spend"}
    if df_camp.empty or not needed.issubset(df_camp.columns):
        return _empty_chart("Sem dados de eficiência por campanha")

    df = df_camp[df_camp["spend"] > 0].copy()
    if df.empty:
        return _empty_chart("Sem campanhas com gasto")

    roas_col = df["ROAS"] if "ROAS" in df.columns else pd.Series([0] * len(df))

    fig = px.scatter(
        df,
        x="ctr",
        y="cpc",
        size="spend",
        color=roas_col,
        color_continuous_scale=["#DC2626", "#F59E0B", "#059669"],
        range_color=[0, max(roas_col.max(), 1)],
        hover_name="campaign_name",
        labels={"ctr": "CTR (%)", "cpc": "CPC (R$)", "color": "ROAS"},
        custom_data=["campaign_name", "spend"] if "spend" in df.columns else ["campaign_name"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "CTR: %{x:.2f}%<br>"
            "CPC: R$ %{y:.2f}<br>"
            "Gasto: R$ %{customdata[1]:,.2f}<extra></extra>"
        )
    )
    fig.update_layout(
        title="Eficiência por Campanha (CTR × CPC)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#E2E8F0"),
        yaxis=dict(gridcolor="#E2E8F0"),
        coloraxis_colorbar=dict(title="ROAS"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def chart_fb_spend_vs_receita(df_camp: "pd.DataFrame") -> "go.Figure":
    """Barras agrupadas: Gasto vs Receita por campanha (top 10 por receita)."""
    needed = {"campaign_name", "spend", "receita"}
    if df_camp.empty or not needed.issubset(df_camp.columns):
        return _empty_chart("Sem dados de gasto × receita")

    df = df_camp[df_camp["spend"] > 0].nlargest(10, "receita")
    if df.empty:
        return _empty_chart("Sem campanhas com dados")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Gasto",
        x=df["campaign_name"],
        y=df["spend"],
        marker_color="#DC2626",
        hovertemplate="<b>%{x}</b><br>Gasto: R$ %{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Receita",
        x=df["campaign_name"],
        y=df["receita"],
        marker_color="#059669",
        hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="Gasto vs Receita por Campanha (Top 10)",
        barmode="group",
        xaxis_title=None,
        yaxis_title="R$",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#E2E8F0"),
        xaxis=dict(tickangle=-30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def chart_fb_ctr_por_campanha(df_camp: "pd.DataFrame") -> "go.Figure":
    """Barra horizontal: CTR por campanha."""
    if df_camp.empty or "campaign_name" not in df_camp.columns or "ctr" not in df_camp.columns:
        return _empty_chart("Sem dados de CTR")

    df = df_camp[df_camp["ctr"] > 0].sort_values("ctr").tail(12)
    if df.empty:
        return _empty_chart("Sem dados de CTR")

    fig = px.bar(
        df,
        x="ctr",
        y="campaign_name",
        orientation="h",
        color="ctr",
        color_continuous_scale=["#F59E0B", "#059669"],
        labels={"ctr": "CTR (%)", "campaign_name": "Campanha"},
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>CTR: %{x:.2f}%<extra></extra>",
    )
    fig.update_layout(
        title="CTR por Campanha",
        xaxis_title="CTR (%)",
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#E2E8F0"),
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def _empty_chart(message: str) -> go.Figure:
    """Retorna um gráfico vazio com mensagem."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#94A3B8"),
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig
