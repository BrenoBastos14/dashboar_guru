"""Designer Visual de Funil — ActiveCampaign."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import streamlit as st

from utils.activecampaign import ActiveCampaignClient

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Designer de Funil — AC",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRIGGER_TYPES = [
    "Tag adicionada",
    "Formulário enviado",
    "Contato criado",
    "Entrando em lista",
    "Data específica",
    "Webhook externo",
    "Manual",
]

STAGE_COLORS = [
    "#4C9BE8",  # blue
    "#7B61FF",  # purple
    "#F59E0B",  # amber
    "#10B981",  # green
    "#EF4444",  # red
    "#EC4899",  # pink
    "#06B6D4",  # cyan
    "#84CC16",  # lime
]

ACTION_TYPES = [
    "Enviar email",
    "Adicionar tag",
    "Remover tag",
    "Aguardar X dias",
    "Mover para lista",
    "Atualizar campo",
    "Criar negócio (deal)",
    "Notificar equipe",
]

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
def _init_state() -> None:
    if "fb_stages" not in st.session_state:
        st.session_state.fb_stages: list[dict] = []
    if "fb_connections" not in st.session_state:
        st.session_state.fb_connections: list[dict] = []
    if "fb_client" not in st.session_state:
        st.session_state.fb_client = None
    if "fb_connected" not in st.session_state:
        st.session_state.fb_connected = False
    if "fb_publish_log" not in st.session_state:
        st.session_state.fb_publish_log: list[dict] = []
    if "fb_editing_stage" not in st.session_state:
        st.session_state.fb_editing_stage: str | None = None

_init_state()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _stage_by_id(sid: str) -> dict | None:
    return next((s for s in st.session_state.fb_stages if s["id"] == sid), None)


def _build_dot() -> str:
    stages = st.session_state.fb_stages
    connections = st.session_state.fb_connections

    lines = [
        'digraph funnel {',
        '  rankdir=LR;',
        '  graph [bgcolor="#0E1117" fontname="Arial"];',
        '  node [shape=box style="filled,rounded" fontname="Arial" fontsize=12 margin="0.3,0.2"];',
        '  edge [fontname="Arial" fontsize=10 color="#AAAAAA" fontcolor="#CCCCCC"];',
    ]

    for i, s in enumerate(stages):
        color = s.get("color", STAGE_COLORS[i % len(STAGE_COLORS)])
        actions_text = ""
        if s.get("actions"):
            actions_text = "\\n" + "\\n".join(
                f"  • {a['type']}" + (f": {a['value']}" if a.get("value") else "")
                for a in s["actions"]
            )
        label = f"{s['name']}\\n[{s['trigger']}]{actions_text}"
        node_id = f'node_{s["id"].replace("-", "_")}'
        lines.append(
            f'  {node_id} [label="{label}" fillcolor="{color}" fontcolor="white"];'
        )

    for c in connections:
        src = _stage_by_id(c["from"])
        tgt = _stage_by_id(c["to"])
        if not src or not tgt:
            continue
        src_id = f'node_{c["from"].replace("-", "_")}'
        tgt_id = f'node_{c["to"].replace("-", "_")}'
        bridge_tag = f'bridge_{_slug(src["name"])}→{_slug(tgt["name"])}'
        label = c.get("label") or f"Tag: {bridge_tag}"
        lines.append(f'  {src_id} -> {tgt_id} [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


def _build_guide() -> list[dict]:
    """Generate manual setup guide for steps that can't be created via API."""
    guide = []
    stages = st.session_state.fb_stages
    connections = st.session_state.fb_connections

    for i, s in enumerate(stages):
        steps = []

        # Entry trigger instructions
        trigger = s.get("trigger", "Manual")
        if trigger == "Tag adicionada":
            steps.append(f"Trigger: 'The contact is added to a tag' → selecione a tag de entrada desta etapa.")
        elif trigger == "Formulário enviado":
            steps.append("Trigger: 'Submits a form' → selecione o formulário de entrada.")
        elif trigger == "Contato criado":
            steps.append("Trigger: 'Contact is created'.")
        elif trigger == "Entrando em lista":
            steps.append("Trigger: 'Subscribes to a list' → selecione a lista desta etapa.")
        else:
            steps.append(f"Trigger: configure manualmente como '{trigger}'.")

        # Actions
        for action in s.get("actions", []):
            atype = action.get("type", "")
            aval = action.get("value", "")
            if atype == "Enviar email":
                steps.append(f"Ação: 'Send an email' → selecione o email '{aval or 'configure email'}'.")
            elif atype == "Adicionar tag":
                steps.append(f"Ação: 'Add tag' → selecione/crie a tag '{aval}'.")
            elif atype == "Remover tag":
                steps.append(f"Ação: 'Remove tag' → selecione a tag '{aval}'.")
            elif atype == "Aguardar X dias":
                steps.append(f"Ação: 'Wait' → {aval or 'X'} dia(s).")
            elif atype == "Mover para lista":
                steps.append(f"Ação: 'Subscribe to list' → selecione a lista '{aval}'.")
            elif atype == "Criar negócio (deal)":
                steps.append(f"Ação: 'Add a deal' → configure pipeline e estágio.")
            elif atype == "Notificar equipe":
                steps.append(f"Ação: 'Notify someone' → configure email de notificação para '{aval}'.")
            else:
                steps.append(f"Ação: configure '{atype}'" + (f" com valor '{aval}'" if aval else "") + ".")

        # Outgoing connections — add bridge tag as last action
        outgoing = [c for c in connections if c["from"] == s["id"]]
        for c in outgoing:
            tgt = _stage_by_id(c["to"])
            if tgt:
                bridge_tag = f"bridge_{_slug(s['name'])}_{_slug(tgt['name'])}"
                steps.append(
                    f"Última ação: 'Add tag' → adicione a tag de bridge '{bridge_tag}' "
                    f"para disparar a próxima automação '{tgt['name']}'."
                )

        guide.append({"stage": s["name"], "automation_name": f"[Funil] {s['name']}", "steps": steps})

    return guide


# ---------------------------------------------------------------------------
# Sidebar — Conexão AC
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🔀 Designer de Funil")
    st.markdown("---")

    with st.form("fb_connect_form"):
        account_url = st.text_input("URL da Conta AC", placeholder="https://suaconta.api-us1.com")
        api_key = st.text_input("API Key", type="password")
        connect_btn = st.form_submit_button("Conectar ao AC", use_container_width=True, type="primary")

    if connect_btn:
        if account_url and api_key:
            with st.spinner("Conectando..."):
                client = ActiveCampaignClient(account_url.strip(), api_key.strip())
                ok, msg = client.test_connection()
            if ok:
                st.success(msg)
                st.session_state.fb_client = client
                st.session_state.fb_connected = True
            else:
                st.error(msg)
        else:
            st.warning("Preencha URL e API Key.")

    if st.session_state.fb_connected:
        st.success("Conectado ao AC")

    st.markdown("---")

    # Funnel actions
    if st.session_state.fb_stages:
        if st.button("Limpar Funil", use_container_width=True, type="secondary"):
            st.session_state.fb_stages = []
            st.session_state.fb_connections = []
            st.session_state.fb_publish_log = []
            st.rerun()

        # Export funnel as JSON
        funnel_json = json.dumps(
            {"stages": st.session_state.fb_stages, "connections": st.session_state.fb_connections},
            ensure_ascii=False,
            indent=2,
        )
        st.download_button(
            "Exportar Funil (JSON)",
            data=funnel_json,
            file_name="funil_ac.json",
            mime="application/json",
            use_container_width=True,
        )

    st.caption("Designer de Funil v1.0")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("🔀 Designer Visual de Funil — ActiveCampaign")
st.caption("Desenhe o fluxo do seu funil, conecte as etapas e publique direto no AC.")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_build, tab_visual, tab_publish = st.tabs(["🧱 Construir Funil", "👁 Visualização", "🚀 Publicar no AC"])

# ===========================================================================
# TAB 1 — Construir
# ===========================================================================
with tab_build:
    left_col, right_col = st.columns([1, 1], gap="large")

    # ----- ADD STAGE -----
    with left_col:
        st.subheader("Adicionar Etapa")

        with st.form("add_stage_form", clear_on_submit=True):
            stage_name = st.text_input("Nome da Etapa *", placeholder="Ex: Lead Captado")
            trigger = st.selectbox("Tipo de Disparo", TRIGGER_TYPES)
            color_idx = st.selectbox(
                "Cor",
                list(range(len(STAGE_COLORS))),
                format_func=lambda i: ["Azul", "Roxo", "Âmbar", "Verde", "Vermelho", "Rosa", "Ciano", "Lima"][i],
            )

            st.markdown("**Ações desta etapa** (opcional)")
            action_cols = st.columns([2, 3])
            with action_cols[0]:
                action_type = st.selectbox("Tipo", ACTION_TYPES, key="action_type_select")
            with action_cols[1]:
                action_value = st.text_input("Valor / Nome", placeholder="Ex: email_boas_vindas", key="action_value_input")

            add_more_action = st.checkbox("Adicionar mais ações depois")

            submitted = st.form_submit_button("Adicionar Etapa", use_container_width=True, type="primary")

        if submitted:
            if not stage_name.strip():
                st.error("O nome da etapa é obrigatório.")
            else:
                actions = []
                if action_type:
                    actions.append({"type": action_type, "value": action_value.strip()})
                stage = {
                    "id": str(uuid.uuid4()),
                    "name": stage_name.strip(),
                    "trigger": trigger,
                    "color": STAGE_COLORS[color_idx],
                    "actions": actions,
                }
                st.session_state.fb_stages.append(stage)
                st.session_state.fb_editing_stage = stage["id"] if add_more_action else None
                st.success(f"Etapa '{stage_name}' adicionada!")
                st.rerun()

    # ----- CONNECT STAGES -----
    with right_col:
        st.subheader("Conectar Etapas")

        stages = st.session_state.fb_stages
        if len(stages) < 2:
            st.info("Adicione pelo menos 2 etapas para criar conexões.")
        else:
            stage_names = {s["id"]: s["name"] for s in stages}
            stage_ids = [s["id"] for s in stages]

            with st.form("connect_form", clear_on_submit=True):
                from_id = st.selectbox("Da etapa", stage_ids, format_func=lambda x: stage_names[x], key="conn_from")
                to_id = st.selectbox("Para a etapa", stage_ids, format_func=lambda x: stage_names[x], key="conn_to")
                conn_label = st.text_input("Rótulo da conexão (opcional)", placeholder="Ex: Converteu, Não abriu email")
                conn_submitted = st.form_submit_button("Conectar", use_container_width=True, type="primary")

            if conn_submitted:
                if from_id == to_id:
                    st.error("Selecione etapas diferentes.")
                else:
                    existing = any(
                        c["from"] == from_id and c["to"] == to_id
                        for c in st.session_state.fb_connections
                    )
                    if existing:
                        st.warning("Essa conexão já existe.")
                    else:
                        st.session_state.fb_connections.append({
                            "id": str(uuid.uuid4()),
                            "from": from_id,
                            "to": to_id,
                            "label": conn_label.strip(),
                        })
                        st.success(f"Conectado: {stage_names[from_id]} → {stage_names[to_id]}")
                        st.rerun()

    st.markdown("---")

    # ----- CURRENT STAGES -----
    if st.session_state.fb_stages:
        st.subheader("Etapas do Funil")

        for i, s in enumerate(list(st.session_state.fb_stages)):
            with st.expander(f"**{i+1}. {s['name']}** — Disparo: {s['trigger']}", expanded=False):
                ecol1, ecol2 = st.columns([4, 1])
                with ecol1:
                    st.markdown(f"**Cor:** <span style='background:{s['color']};padding:2px 12px;border-radius:4px;color:white'>▌</span>", unsafe_allow_html=True)
                    if s.get("actions"):
                        st.markdown("**Ações configuradas:**")
                        for a in s["actions"]:
                            val = f": *{a['value']}*" if a.get("value") else ""
                            st.markdown(f"  - {a['type']}{val}")
                    else:
                        st.caption("Nenhuma ação configurada ainda.")

                    # Add action inline
                    with st.form(f"add_action_{s['id']}", clear_on_submit=True):
                        ac1, ac2, ac3 = st.columns([2, 3, 1])
                        with ac1:
                            new_atype = st.selectbox("Tipo de ação", ACTION_TYPES, key=f"atype_{s['id']}")
                        with ac2:
                            new_aval = st.text_input("Valor", key=f"aval_{s['id']}", placeholder="Opcional")
                        with ac3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            add_action_btn = st.form_submit_button("+ Ação")
                        if add_action_btn:
                            s["actions"].append({"type": new_atype, "value": new_aval.strip()})
                            st.rerun()

                with ecol2:
                    if st.button("Remover", key=f"del_stage_{s['id']}", type="secondary"):
                        st.session_state.fb_stages = [x for x in st.session_state.fb_stages if x["id"] != s["id"]]
                        st.session_state.fb_connections = [
                            c for c in st.session_state.fb_connections
                            if c["from"] != s["id"] and c["to"] != s["id"]
                        ]
                        st.rerun()

        # Connections list
        if st.session_state.fb_connections:
            st.subheader("Conexões")
            for c in list(st.session_state.fb_connections):
                src = _stage_by_id(c["from"])
                tgt = _stage_by_id(c["to"])
                if src and tgt:
                    ccol1, ccol2 = st.columns([5, 1])
                    with ccol1:
                        label_text = f" *({c['label']})*" if c.get("label") else ""
                        st.markdown(f"**{src['name']}** → **{tgt['name']}**{label_text}")
                    with ccol2:
                        if st.button("✕", key=f"del_conn_{c['id']}"):
                            st.session_state.fb_connections = [
                                x for x in st.session_state.fb_connections if x["id"] != c["id"]
                            ]
                            st.rerun()
    else:
        st.info("Nenhuma etapa adicionada ainda. Use o formulário acima para começar.")

# ===========================================================================
# TAB 2 — Visual
# ===========================================================================
with tab_visual:
    if not st.session_state.fb_stages:
        st.info("Adicione etapas na aba 'Construir Funil' para visualizar o fluxo.")
    else:
        st.subheader("Fluxo Visual do Funil")
        dot = _build_dot()
        st.graphviz_chart(dot, use_container_width=True)

        # Legend
        with st.expander("Legenda"):
            st.markdown("""
- **Nós (caixas)**: cada etapa do funil com seu tipo de disparo e ações
- **Setas**: conexões entre etapas; o rótulo indica a **tag de bridge** criada no AC
- As **tags de bridge** são criadas automaticamente ao publicar
            """)

        # Show dot source
        with st.expander("Ver código do diagrama (DOT)"):
            st.code(dot, language="dot")

# ===========================================================================
# TAB 3 — Publicar
# ===========================================================================
with tab_publish:
    stages = st.session_state.fb_stages
    connections = st.session_state.fb_connections

    if not stages:
        st.info("Construa o funil primeiro na aba 'Construir Funil'.")
        st.stop()

    st.subheader("Resumo do que será criado no AC")

    # Tags to create
    tags_to_create = []
    for c in connections:
        src = _stage_by_id(c["from"])
        tgt = _stage_by_id(c["to"])
        if src and tgt:
            tags_to_create.append(f"bridge_{_slug(src['name'])}_{_slug(tgt['name'])}")

    # Extra tags from actions
    for s in stages:
        for a in s.get("actions", []):
            if a.get("type") in ("Adicionar tag", "Remover tag") and a.get("value"):
                tags_to_create.append(a["value"])

    # Deduplicate
    tags_to_create = list(dict.fromkeys(tags_to_create))

    # Automations to create
    automations_to_create = [f"[Funil] {s['name']}" for s in stages]

    col_tags, col_autos = st.columns(2)
    with col_tags:
        st.markdown(f"**Tags a criar ({len(tags_to_create)})**")
        for t in tags_to_create:
            st.markdown(f"- `{t}`")
        if not tags_to_create:
            st.caption("Nenhuma tag de bridge necessária (adicione conexões entre etapas).")

    with col_autos:
        st.markdown(f"**Automações a criar ({len(automations_to_create)})**")
        for a in automations_to_create:
            st.markdown(f"- `{a}`")

    st.markdown("---")

    # Publish button
    if not st.session_state.fb_connected:
        st.warning("Conecte sua conta AC na barra lateral antes de publicar.")
    else:
        if st.button("🚀 Publicar no ActiveCampaign", type="primary", use_container_width=False):
            client: ActiveCampaignClient = st.session_state.fb_client
            log = []

            progress = st.progress(0, text="Iniciando publicação...")
            total_ops = len(tags_to_create) + len(automations_to_create)
            done = 0

            # Create tags
            for tag_name in tags_to_create:
                try:
                    created = client.create_tag(
                        name=tag_name,
                        tag_type="contact",
                        description="Criada pelo Designer de Funil",
                    )
                    log.append({"tipo": "Tag", "nome": tag_name, "status": "✅ Criada", "id": created.get("id", "")})
                except Exception as e:  # noqa: BLE001
                    err = str(e)
                    if "422" in err or "duplicate" in err.lower():
                        log.append({"tipo": "Tag", "nome": tag_name, "status": "⚠️ Já existe", "id": "-"})
                    else:
                        log.append({"tipo": "Tag", "nome": tag_name, "status": f"❌ Erro: {e}", "id": ""})
                done += 1
                progress.progress(done / total_ops, text=f"Criando tag: {tag_name}")

            # Create automations
            for auto_name in automations_to_create:
                try:
                    created = client.create_automation(name=auto_name, status=0)
                    log.append({"tipo": "Automação", "nome": auto_name, "status": "✅ Criada (inativa)", "id": created.get("id", "")})
                except Exception as e:  # noqa: BLE001
                    log.append({"tipo": "Automação", "nome": auto_name, "status": f"❌ Erro: {e}", "id": ""})
                done += 1
                progress.progress(done / total_ops, text=f"Criando automação: {auto_name}")

            progress.progress(1.0, text="Concluído!")
            st.session_state.fb_publish_log = log
            st.rerun()

    # Show publish log
    if st.session_state.fb_publish_log:
        st.success("Publicação concluída!")
        import pandas as pd
        log_df = pd.DataFrame(st.session_state.fb_publish_log)
        st.dataframe(log_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Manual setup guide
    st.subheader("📋 Guia de Configuração Manual")
    st.markdown(
        "As automações foram criadas como **rascunhos inativos** no AC. "
        "Siga o guia abaixo para configurar os steps internos de cada uma:"
    )

    guide = _build_guide()
    for i, item in enumerate(guide):
        with st.expander(f"**{i+1}. {item['automation_name']}**", expanded=i == 0):
            st.markdown(f"Abra a automação `{item['automation_name']}` no painel do ActiveCampaign e adicione:")
            for j, step in enumerate(item["steps"]):
                st.markdown(f"**Passo {j+1}:** {step}")
            if not item["steps"]:
                st.caption("Nenhuma ação configurada para esta etapa.")

    if not guide:
        st.info("Adicione etapas ao funil para ver o guia de configuração.")
