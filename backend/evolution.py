import httpx

from .config import EVOLUTION_API_KEY, EVOLUTION_URL, EVOLUTION_WEBHOOK_URL


DEFAULT_EVENTS = [
    "MESSAGES_UPSERT",
    "QRCODE_UPDATED",
    "CONNECTION_UPDATE",
]


def _headers() -> dict:
    return {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}


async def create_instance(name: str, webhook_url: str | None = None) -> dict:
    url = f"{EVOLUTION_URL}/instance/create"
    payload = {
        "instanceName": name,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
        "webhook": {
            "url": webhook_url or EVOLUTION_WEBHOOK_URL,
            "byEvents": False,
            "base64": True,
            "events": DEFAULT_EVENTS,
        },
    }
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(url, json=payload, headers=_headers())
        r.raise_for_status()
        return r.json()


async def connect_instance(name: str) -> dict:
    """Returns QR code data (base64) for pairing."""
    url = f"{EVOLUTION_URL}/instance/connect/{name}"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, headers=_headers())
        r.raise_for_status()
        return r.json()


async def fetch_instance(name: str) -> dict:
    url = f"{EVOLUTION_URL}/instance/fetchInstances"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, params={"instanceName": name}, headers=_headers())
        r.raise_for_status()
        return r.json()


async def logout_instance(name: str) -> dict:
    url = f"{EVOLUTION_URL}/instance/logout/{name}"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.delete(url, headers=_headers())
        return r.json() if r.content else {}


async def delete_instance(name: str) -> dict:
    url = f"{EVOLUTION_URL}/instance/delete/{name}"
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.delete(url, headers=_headers())
        return r.json() if r.content else {}


async def send_text(instance_name: str, number: str, text: str) -> dict:
    url = f"{EVOLUTION_URL}/message/sendText/{instance_name}"
    payload = {"number": number, "text": text}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(url, json=payload, headers=_headers())
        r.raise_for_status()
        return r.json()
