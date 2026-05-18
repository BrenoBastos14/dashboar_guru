from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db, evolution, llm
from .config import DEFAULT_SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("whatsapp-bot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    log.info("Database initialized at %s", db.DB_PATH if hasattr(db, "DB_PATH") else "")
    yield


app = FastAPI(title="WhatsApp LLM Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    """Pull text from the various WhatsApp message shapes Evolution forwards."""
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
    # ignore image/audio/etc for now
    return None


def _normalize_number(jid: str) -> str:
    # JIDs @lid (Linked Device IDs do Baileys/WhatsApp moderno) não são
    # números de telefone — a Evolution API aceita o JID completo nesse caso.
    if jid.endswith("@lid"):
        return jid
    return jid.split("@")[0]


def _is_group(jid: str) -> bool:
    return jid.endswith("@g.us") or jid.endswith("@broadcast")


# ---------------------------------------------------------------------------
# Instance management
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/instances")
async def get_instances():
    return db.list_instances()


@app.post("/instances")
async def create_instance(payload: CreateInstanceRequest):
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

    db.upsert_instance(payload.name, payload.system_prompt or DEFAULT_SYSTEM_PROMPT)
    return {
        "evolution": evo,
        "instance": db.get_instance(payload.name),
        "webhook_warning": webhook_warning,
    }


@app.post("/instances/{name}/webhook")
async def reset_webhook(name: str):
    if not db.get_instance(name):
        raise HTTPException(404, "Instance not found")
    try:
        return await evolution.set_webhook(name)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Evolution API unreachable: {e}")


@app.get("/instances/{name}/qrcode")
async def get_qr(name: str):
    try:
        return await evolution.connect_instance(name)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Evolution API unreachable: {e}")


@app.put("/instances/{name}/prompt")
async def update_prompt(name: str, payload: UpdatePromptRequest):
    if not db.get_instance(name):
        raise HTTPException(404, "Instance not found")
    db.update_instance_prompt(name, payload.system_prompt)
    return db.get_instance(name)


@app.put("/instances/{name}/enabled")
async def toggle_enabled(name: str, payload: EnableRequest):
    if not db.get_instance(name):
        raise HTTPException(404, "Instance not found")
    db.set_instance_enabled(name, payload.enabled)
    return db.get_instance(name)


@app.delete("/instances/{name}")
async def remove_instance(name: str):
    for action in (evolution.logout_instance, evolution.delete_instance):
        try:
            await action(name)
        except Exception:
            log.warning("Failed %s on %s", action.__name__, name, exc_info=True)
    db.delete_instance(name)
    return {"ok": True}


@app.get("/instances/{name}/conversations")
async def conversations(name: str):
    return db.recent_conversations(name)


@app.get("/instances/{name}/conversations/{jid}")
async def conversation(name: str, jid: str):
    return db.history(name, jid, limit=200)


# ---------------------------------------------------------------------------
# Webhook
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
