from __future__ import annotations

from openai import AsyncOpenAI

from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError(
                "DEEPSEEK_API_KEY não configurada. Defina a variável no .env."
            )
        _client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client


async def chat(system_prompt: str, history: list[dict], user_message: str) -> str:
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for m in history:
        role = m.get("role")
        if role in ("user", "assistant") and m.get("content"):
            messages.append({"role": role, "content": m["content"]})
    messages.append({"role": "user", "content": user_message})

    resp = await _get_client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )
    return (resp.choices[0].message.content or "").strip()
