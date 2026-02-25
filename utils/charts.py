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
