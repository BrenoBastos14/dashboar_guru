import base64
import os

import requests
import streamlit as st


st.set_page_config(page_title="WhatsApp Bot", page_icon="💬", layout="wide")

DEFAULT_API = os.getenv("WHATSAPP_BACKEND_URL", "http://localhost:8000")
DEFAULT_WEBHOOK = os.getenv(
    "WHATSAPP_DEFAULT_WEBHOOK", "http://host.docker.internal:8000/webhook"
)
DEFAULT_PROMPT = (
    "Você é um atendente virtual atencioso e útil. "
    "Responda de forma breve, clara e em português, com tom amigável."
)


with st.sidebar:
    st.markdown("### Configurações")
    api_base = st.text_input(
        "Backend URL",
        value=st.session_state.get("api_base", DEFAULT_API),
        help="URL onde o FastAPI está rodando (ex: http://localhost:8000).",
    ).rstrip("/")
    st.session_state["api_base"] = api_base


def api(path: str, method: str = "GET", **kwargs):
    url = f"{api_base}{path}"
    r = requests.request(method, url, timeout=60, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


st.title("💬 WhatsApp + LLM Bot")
st.caption(
    "Conecte um número de WhatsApp via Evolution API e deixe a IA (DeepSeek) "
    "responder automaticamente quem chamar."
)

tab_lista, tab_nova = st.tabs(["📋 Minhas instâncias", "➕ Nova instância"])

# ---------------------------------------------------------------------------
# Nova instância
# ---------------------------------------------------------------------------
with tab_nova:
    with st.form("new_instance"):
        name = st.text_input(
            "Nome da instância",
            help="Sem espaços ou acentos. Ex: cliente-joao",
        )
        sys_prompt = st.text_area(
            "Prompt do sistema (personalidade do bot)",
            value=DEFAULT_PROMPT,
            height=160,
        )
        webhook_url = st.text_input(
            "URL do webhook",
            value=DEFAULT_WEBHOOK,
            help=(
                "Para onde a Evolution envia eventos. Em Docker Desktop use "
                "`host.docker.internal:8000`. Em produção, a URL pública do seu backend."
            ),
        )
        submitted = st.form_submit_button("Criar instância", type="primary")

    if submitted:
        if not name.strip():
            st.error("Defina um nome.")
        else:
            try:
                api(
                    "/instances",
                    method="POST",
                    json={
                        "name": name.strip(),
                        "system_prompt": sys_prompt,
                        "webhook_url": webhook_url,
                    },
                )
                st.success(
                    f"Instância **{name}** criada. Abra a aba **📋 Minhas instâncias** "
                    "e gere o QR code para parear o WhatsApp do cliente."
                )
            except requests.HTTPError as e:
                st.error(f"Erro ao criar instância: {e.response.text}")
            except Exception as e:
                st.error(f"Erro ao falar com o backend: {e}")

# ---------------------------------------------------------------------------
# Lista de instâncias
# ---------------------------------------------------------------------------
with tab_lista:
    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("🔄 Atualizar"):
            st.rerun()

    try:
        instances = api("/instances")
    except Exception as e:
        st.error(
            f"Não consegui falar com o backend em **{api_base}**.\n\n"
            "Verifique se o FastAPI está rodando: "
            "`uvicorn backend.main:app --reload --port 8000`\n\n"
            f"Detalhe: {e}"
        )
        st.stop()

    if not instances:
        st.info("Nenhuma instância criada ainda. Vá para a aba **➕ Nova instância**.")

    for inst in instances:
        name = inst["name"]
        status = inst.get("status") or "desconhecido"
        connected = status in ("open", "connected")

        with st.container(border=True):
            head = st.columns([3, 2, 1])
            with head[0]:
                st.markdown(f"### {name}")
                badge = "🟢" if connected else ("🟡" if status == "connecting" else "🔴")
                st.caption(f"{badge} Status: **{status}**")
            with head[1]:
                st.caption(
                    f"Bot {'ativo ✅' if inst.get('enabled') else 'pausado ⏸️'}"
                )
            with head[2]:
                enabled_now = bool(inst.get("enabled"))
                new_val = st.toggle(
                    "Ativo", value=enabled_now, key=f"toggle_{name}"
                )
                if new_val != enabled_now:
                    api(
                        f"/instances/{name}/enabled",
                        method="PUT",
                        json={"enabled": new_val},
                    )
                    st.rerun()

            with st.expander(
                "📱 QR Code / Conexão", expanded=not connected
            ):
                btn_cols = st.columns([1, 1, 4])
                with btn_cols[0]:
                    gen = st.button("Gerar QR", key=f"qr_btn_{name}")
                with btn_cols[1]:
                    refresh = st.button("Atualizar status", key=f"st_btn_{name}")

                if gen:
                    try:
                        st.session_state[f"qr_data_{name}"] = api(
                            f"/instances/{name}/qrcode"
                        )
                    except Exception as e:
                        st.error(f"Erro ao gerar QR: {e}")

                if refresh:
                    st.rerun()

                qr = st.session_state.get(f"qr_data_{name}")
                if connected:
                    st.success("Conectado ✅ — o bot está ouvindo este número.")
                elif qr:
                    b64 = qr.get("base64") or qr.get("qrcode") or ""
                    if isinstance(b64, dict):
                        b64 = b64.get("base64") or b64.get("code") or ""
                    try:
                        if b64.startswith("data:image"):
                            st.image(b64, width=320)
                        elif b64:
                            raw = b64.split(",")[-1]
                            st.image(base64.b64decode(raw), width=320)
                    except Exception as e:
                        st.warning(f"Não consegui renderizar o QR: {e}")
                        st.json(qr)
                    code = qr.get("code") or qr.get("pairingCode")
                    if code:
                        st.caption(f"Código de pareamento: `{code}`")
                    st.info(
                        "Abra o WhatsApp no celular do cliente → "
                        "**Aparelhos conectados** → **Conectar um aparelho** → "
                        "escaneie o QR acima."
                    )
                else:
                    st.caption("Clique em **Gerar QR** para começar o pareamento.")

            with st.expander("🧠 Prompt do bot"):
                new_prompt = st.text_area(
                    "Personalidade / instruções",
                    value=inst.get("system_prompt") or "",
                    height=180,
                    key=f"prompt_{name}",
                )
                if st.button("Salvar prompt", key=f"save_prompt_{name}"):
                    api(
                        f"/instances/{name}/prompt",
                        method="PUT",
                        json={"system_prompt": new_prompt},
                    )
                    st.success("Prompt atualizado.")
                    st.rerun()

            with st.expander("💬 Conversas recentes"):
                try:
                    convs = api(f"/instances/{name}/conversations")
                except Exception as e:
                    convs = []
                    st.caption(f"Erro: {e}")
                if not convs:
                    st.caption("Nenhuma conversa registrada ainda.")
                else:
                    for c in convs:
                        jid = c["jid"]
                        st.markdown(
                            f"**{jid.split('@')[0]}** — {c['n_messages']} msgs · "
                            f"última em {c['last_at']}"
                        )
                        if st.button("Ver", key=f"view_{name}_{jid}"):
                            msgs = api(f"/instances/{name}/conversations/{jid}")
                            for m in msgs:
                                with st.chat_message(m["role"]):
                                    st.write(m["content"])

            with st.expander("🗑️ Remover instância"):
                st.warning(
                    "Isso desconecta o WhatsApp na Evolution API e apaga o histórico local."
                )
                if st.button(
                    f"Remover **{name}**",
                    type="secondary",
                    key=f"del_{name}",
                ):
                    api(f"/instances/{name}", method="DELETE")
                    st.success("Removida.")
                    st.rerun()
