from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import auth, db, evolution, llm
from .config import DATABASE_URL, DEFAULT_SYSTEM_PROMPT
from .models import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("whatsapp-bot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    log.info("Database ready at %s", DATABASE_URL.split("@")[-1])
    auth.ensure_admin_user()
    yield


app = FastAPI(title="WhatsApp LLM Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth.router)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateInstanceRequest(BaseModel):
    name: str
    system_prompt: str | None = None
    webhook_url: str | None = None


class UpdatePromptRequest(BaseModel):
    system_prompt: str


class EnableRequest(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text(message: dict | None) -> str | None:
    if not message:
        return None
    conv = message.get("conversation")
    if isinstance(conv, str) and conv.strip():
        return conv
    ext = message.get("extendedTextMessage")
    if isinstance(ext, dict):
        text = ext.get("text")
        if text:
            return text
    return None


def _normalize_number(jid: str) -> str:
    # JIDs @lid (Linked Device IDs do Baileys/WhatsApp moderno) não são
    # números de telefone — a Evolution API aceita o JID completo nesse caso.
    if jid.endswith("@lid"):
        return jid
    return jid.split("@")[0]


def _is_group(jid: str) -> bool:
    return jid.endswith("@g.us") or jid.endswith("@broadcast")


def _require_owned(name: str, user: User) -> dict:
    inst = db.get_instance(name)
    if inst is None:
        raise HTTPException(404, "Instance not found")
    if inst.get("owner_user_id") not in (None, user.id) and not user.is_admin:
        raise HTTPException(403, "Você não tem acesso a essa instância")
    return inst


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# Instance management (autenticado)
# ---------------------------------------------------------------------------

@app.get("/instances")
async def get_instances(user: User = Depends(auth.require_user)):
    if user.is_admin:
        return db.list_instances()
    return db.list_instances(owner_user_id=user.id)


@app.post("/instances")
async def create_instance(
    payload: CreateInstanceRequest, user: User = Depends(auth.require_user)
):
    if db.get_instance(payload.name):
        raise HTTPException(409, "Já existe uma instância com esse nome")
    try:
        evo = await evolution.create_instance(payload.name, payload.webhook_url)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Evolution API unreachable: {e}")

    webhook_warning: str | None = None
    try:
        await evolution.set_webhook(payload.name, payload.webhook_url)
    except httpx.HTTPStatusError as e:
        webhook_warning = f"set_webhook falhou ({e.response.status_code}): {e.response.text}"
        log.warning(webhook_warning)
    except httpx.HTTPError as e:
        webhook_warning = f"set_webhook unreachable: {e}"
        log.warning(webhook_warning)

    db.upsert_instance(
        payload.name,
        payload.system_prompt or DEFAULT_SYSTEM_PROMPT,
        owner_user_id=user.id,
    )
    return {
        "evolution": evo,
        "instance": db.get_instance(payload.name),
        "webhook_warning": webhook_warning,
    }


@app.post("/instances/{name}/webhook")
async def reset_webhook(name: str, user: User = Depends(auth.require_user)):
    _require_owned(name, user)
    try:
        return await evolution.set_webhook(name)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Evolution API unreachable: {e}")


@app.get("/instances/{name}/qrcode")
async def get_qr(name: str, user: User = Depends(auth.require_user)):
    _require_owned(name, user)
    try:
        return await evolution.connect_instance(name)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Evolution API unreachable: {e}")


@app.put("/instances/{name}/prompt")
async def update_prompt(
    name: str, payload: UpdatePromptRequest, user: User = Depends(auth.require_user)
):
    _require_owned(name, user)
    db.update_instance_prompt(name, payload.system_prompt)
    return db.get_instance(name)


@app.put("/instances/{name}/enabled")
async def toggle_enabled(
    name: str, payload: EnableRequest, user: User = Depends(auth.require_user)
):
    _require_owned(name, user)
    db.set_instance_enabled(name, payload.enabled)
    return db.get_instance(name)


@app.delete("/instances/{name}")
async def remove_instance(name: str, user: User = Depends(auth.require_user)):
    _require_owned(name, user)
    for action in (evolution.logout_instance, evolution.delete_instance):
        try:
            await action(name)
        except Exception:
            log.warning("Failed %s on %s", action.__name__, name, exc_info=True)
    db.delete_instance(name)
    return {"ok": True}


@app.get("/instances/{name}/conversations")
async def conversations(name: str, user: User = Depends(auth.require_user)):
    _require_owned(name, user)
    return db.recent_conversations(name)


@app.get("/instances/{name}/conversations/{jid}")
async def conversation(name: str, jid: str, user: User = Depends(auth.require_user)):
    _require_owned(name, user)
    return db.history(name, jid, limit=200)


# ---------------------------------------------------------------------------
# Webhook (PÚBLICO — Evolution não envia auth)
# ---------------------------------------------------------------------------

@app.post("/webhook")
@app.post("/webhook/{instance}")
async def webhook(request: Request, instance: str | None = None):
    body = await request.json()
    event = (body.get("event") or "").lower().replace(".", "_")
    inst_name = instance or body.get("instance") or body.get("instanceName") or ""
    data = body.get("data") or {}
    log.info("webhook event=%s instance=%s", event, inst_name)

    if not inst_name:
        return {"ok": True}

    if not db.get_instance(inst_name):
        db.upsert_instance(inst_name)

    if event in ("connection_update",):
        state = data.get("state") or data.get("connection") or "unknown"
        db.update_instance_status(inst_name, str(state))
        return {"ok": True}

    if event in ("messages_upsert",):
        log.info("messages_upsert raw body=%s", body)
        await _handle_message(inst_name, data)
        return {"ok": True}

    return {"ok": True}


async def _handle_message(instance: str, data: dict) -> None:
    key = data.get("key") or {}
    log.info("_handle_message key=%s", key)
    if key.get("fromMe"):
        log.info("skipping fromMe message")
        return
    remote_jid = key.get("remoteJid") or ""
    if not remote_jid:
        log.info("skipping empty remoteJid")
        return
    if _is_group(remote_jid):
        log.info("skipping group message %s", remote_jid)
        return

    msg = data.get("message") or {}
    log.info("message data keys=%s", list(msg.keys()))

    text = _extract_text(msg)
    if not text:
        log.info("no text extracted from message %s", msg)
        return

    inst = db.get_instance(instance)
    if not inst or not inst.get("enabled"):
        log.info("instance %s disabled, ignoring", instance)
        return

    system_prompt = inst.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    hist = db.history(instance, remote_jid)
    db.add_message(instance, remote_jid, "user", text)

    try:
        reply = await llm.chat(system_prompt, hist, text)
    except Exception:
        log.exception("LLM error")
        reply = "Desculpe, tive um problema para gerar a resposta agora. Tente novamente em instantes."

    if not reply:
        return

    db.add_message(instance, remote_jid, "assistant", reply)

    try:
        await evolution.send_text(instance, _normalize_number(remote_jid), reply)
    except httpx.HTTPStatusError as e:
        log.error(
            "send_text %s: status=%s body=%s",
            remote_jid,
            e.response.status_code,
            e.response.text,
        )
    except Exception:
        log.exception("Failed to send reply via Evolution API")
