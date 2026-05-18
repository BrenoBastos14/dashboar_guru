"""Login compartilhado para o app Streamlit (app.py + páginas)."""
from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


BACKEND_URL = os.getenv("WHATSAPP_BACKEND_URL", "http://localhost:8000").rstrip("/")


def _backend_url() -> str:
    return st.session_state.get("api_base", BACKEND_URL)


def is_logged_in() -> bool:
    return bool(st.session_state.get("auth_token"))


def auth_headers() -> dict[str, str]:
    token = st.session_state.get("auth_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def current_user() -> dict[str, Any] | None:
    return st.session_state.get("auth_user")


def do_login(email: str, password: str) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{_backend_url()}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
    except requests.RequestException as e:
        return False, f"Não consegui contatar o backend ({e})."

    if r.status_code == 401:
        return False, "Email ou senha incorretos."
    if r.status_code >= 400:
        return False, f"Erro {r.status_code}: {r.text[:200]}"

    data = r.json()
    st.session_state["auth_token"] = data.get("access_token")
    st.session_state["auth_user"] = data.get("user") or {}
    return True, "ok"


def do_logout() -> None:
    st.session_state.pop("auth_token", None)
    st.session_state.pop("auth_user", None)


def _render_login_form() -> None:
    st.title("🔐 Acesso restrito")
    st.caption("Faça login para acessar o painel.")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", autocomplete="email")
        password = st.text_input("Senha", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)
    if submitted:
        ok, msg = do_login(email.strip(), password)
        if ok:
            st.rerun()
        else:
            st.error(msg)


def require_auth() -> dict[str, Any]:
    """Bloqueia a página até o usuário logar. Retorna dados do usuário."""
    if is_logged_in():
        return current_user() or {}
    _render_login_form()
    st.stop()


def render_sidebar_account() -> None:
    user = current_user() or {}
    with st.sidebar:
        st.markdown("---")
        email = user.get("email") or "—"
        st.caption(f"Logado como **{email}**")
        if st.button("Sair", use_container_width=True, key="auth_logout_btn"):
            do_logout()
            st.rerun()
