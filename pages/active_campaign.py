"""Central de Automações — ActiveCampaign."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from utils.activecampaign import ActiveCampaignClient

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Central AC — Automações",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STATUS_LABELS = {
    "1": "Ativa",
    "0": "Inativa",
}
STATUS_COLORS = {
    "Ativa": "🟢",
    "Inativa": "🔴",
}


def _fmt_status(raw: str) -> str:
    label = STATUS_LABELS.get(str(raw), str(raw))
    return f"{STATUS_COLORS.get(label, '⚪')} {label}"


def _build_df(automations: list[dict]) -> pd.DataFrame:
    rows = []
    for a in automations:
        rows.append(
            {
                "ID": a.get("id", ""),
                "Nome": a.get("name", ""),
                "Status": _fmt_status(a.get("status", "")),
                "Contatos Ativos": int(a.get("activeCount", 0) or 0),
                "Total Completaram": int(a.get("completedCount", 0) or 0),
                "Criada em": a.get("cdate", "")[:10] if a.get("cdate") else "",
                "Atualizada em": a.get("udate", "")[:10] if a.get("udate") else "",
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "ac_connected" not in st.session_state:
    st.session_state.ac_connected = False
if "ac_client" not in st.session_state:
    st.session_state.ac_client = None
if "ac_automations" not in st.session_state:
    st.session_state.ac_automations = []
if "ac_account_name" not in st.session_state:
    st.session_state.ac_account_name = ""

# ---------------------------------------------------------------------------
# Sidebar — conexão
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚡ ActiveCampaign")
    st.markdown("---")

    with st.form("ac_connect_form"):
        account_url = st.text_input(
            "URL da Conta",
            placeholder="https://suaconta.api-us1.com",
            help="Exemplo: https://minhaempresa.api-us1.com",
        )
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Encontre em: Configurações → Desenvolvedor → API Key",
        )
        connect_btn = st.form_submit_button("Conectar", use_container_width=True, type="primary")

    if connect_btn:
        if not account_url or not api_key:
            st.error("Preencha a URL e a API Key.")
        else:
            with st.spinner("Conectando..."):
                client = ActiveCampaignClient(account_url.strip(), api_key.strip())
                ok, msg = client.test_connection()
            if ok:
                st.success(msg)
                st.session_state.ac_connected = True
                st.session_state.ac_client = client
                st.session_state.ac_account_name = account_url.strip()
                st.session_state.ac_automations = []  # reset on new connection
            else:
                st.error(msg)
                st.session_state.ac_connected = False
                st.session_state.ac_client = None

    if st.session_state.ac_connected:
        st.success(f"Conectado")
        if st.button("Desconectar", use_container_width=True):
            st.session_state.ac_connected = False
            st.session_state.ac_client = None
            st.session_state.ac_automations = []
            st.rerun()

    st.markdown("---")
    st.caption("Central de Automações v1.0")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("⚡ Central de Automações — ActiveCampaign")

if not st.session_state.ac_connected:
    st.info("Conecte sua conta ActiveCampaign na barra lateral para começar.")
    st.markdown(
        """
        **Como obter sua API Key:**
        1. Acesse sua conta ActiveCampaign
        2. Vá em **Configurações** → **Desenvolvedor**
        3. Copie a **API Key** e a **URL da API**
        """
    )
    st.stop()

# ---------------------------------------------------------------------------
# Connected state
# ---------------------------------------------------------------------------
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.markdown(f"**Conta:** `{st.session_state.ac_account_name}`")
with col_refresh:
    if st.button("🔄 Atualizar", use_container_width=True):
        st.session_state.ac_automations = []

# Load automations
if not st.session_state.ac_automations:
    with st.spinner("Carregando automações..."):
        try:
            st.session_state.ac_automations = st.session_state.ac_client.list_automations()
        except Exception as e:  # noqa: BLE001
            st.error(f"Erro ao carregar automações: {e}")
            st.stop()

automations: list[dict] = st.session_state.ac_automations

if not automations:
    st.warning("Nenhuma automação encontrada nesta conta.")
    st.stop()

df = _build_df(automations)

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
st.markdown("### Filtros")
fcol1, fcol2, fcol3 = st.columns([3, 2, 2])

with fcol1:
    search = st.text_input("Buscar por nome", placeholder="Digite para filtrar...")

with fcol2:
    status_opts = ["Todos"] + sorted(df["Status"].unique().tolist())
    status_filter = st.selectbox("Status", status_opts)

with fcol3:
    sort_by = st.selectbox("Ordenar por", ["Nome", "Contatos Ativos", "Total Completaram", "Criada em"])

# Apply filters
filtered_df = df.copy()
if search:
    filtered_df = filtered_df[filtered_df["Nome"].str.contains(search, case=False, na=False)]
if status_filter != "Todos":
    filtered_df = filtered_df[filtered_df["Status"] == status_filter]

# Sort
ascending = sort_by == "Nome"
filtered_df = filtered_df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)

# ---------------------------------------------------------------------------
# KPI bar
# ---------------------------------------------------------------------------
st.markdown("---")
k1, k2, k3, k4 = st.columns(4)
total_active = df["Status"].str.contains("Ativa").sum()
total_inactive = df["Status"].str.contains("Inativa").sum()
k1.metric("Total de Automações", len(df))
k2.metric("Ativas", int(total_active))
k3.metric("Inativas", int(total_inactive))
k4.metric("Contatos em Automações", int(df["Contatos Ativos"].sum()))

st.markdown("---")

# ---------------------------------------------------------------------------
# Table with selection
# ---------------------------------------------------------------------------
st.markdown(f"### Automações ({len(filtered_df)} encontradas)")

if filtered_df.empty:
    st.info("Nenhuma automação encontrada com os filtros aplicados.")
    st.stop()

# Use st.dataframe with selection
event = st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row",
    column_config={
        "ID": st.column_config.TextColumn("ID", width="small"),
        "Nome": st.column_config.TextColumn("Nome", width="large"),
        "Status": st.column_config.TextColumn("Status", width="medium"),
        "Contatos Ativos": st.column_config.NumberColumn("Contatos Ativos", width="medium"),
        "Total Completaram": st.column_config.NumberColumn("Total Completaram", width="medium"),
        "Criada em": st.column_config.TextColumn("Criada em", width="small"),
        "Atualizada em": st.column_config.TextColumn("Atualizada em", width="small"),
    },
)

# ---------------------------------------------------------------------------
# Detail panel for selected rows
# ---------------------------------------------------------------------------
selected_rows = event.selection.rows if event and event.selection else []

if selected_rows:
    st.markdown("---")
    st.markdown(f"### Detalhes das Automações Selecionadas ({len(selected_rows)})")

    for row_idx in selected_rows:
        row = filtered_df.iloc[row_idx]
        automation_id = row["ID"]

        # Find raw automation data
        raw = next((a for a in automations if str(a.get("id")) == str(automation_id)), {})

        with st.expander(f"⚡ {row['Nome']}  |  ID: {automation_id}  |  {row['Status']}", expanded=True):
            d1, d2, d3 = st.columns(3)
            d1.metric("Contatos Ativos", int(raw.get("activeCount", 0) or 0))
            d2.metric("Completaram", int(raw.get("completedCount", 0) or 0))
            d3.metric("Saíram", int(raw.get("exited", 0) or 0))

            info_col, meta_col = st.columns(2)
            with info_col:
                st.markdown("**Informações**")
                st.write(f"- **ID:** {automation_id}")
                st.write(f"- **Status:** {row['Status']}")
                st.write(f"- **Criada em:** {row['Criada em']}")
                st.write(f"- **Atualizada em:** {row['Atualizada em']}")
                if raw.get("hidden"):
                    st.write(f"- **Oculta:** {'Sim' if raw.get('hidden') == '1' else 'Não'}")
            with meta_col:
                st.markdown("**Disparo**")
                st.write(f"- **Tipo de entrada:** {raw.get('defaultscreenstep', 'N/A')}")
                if raw.get("userid"):
                    st.write(f"- **Criada por (user ID):** {raw.get('userid')}")

            # Raw JSON toggle
            with st.expander("Ver JSON completo"):
                st.json(raw)
else:
    st.caption("Clique em uma ou mais linhas da tabela para ver os detalhes.")
