import os

from dotenv import load_dotenv

load_dotenv()


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

EVOLUTION_URL = os.getenv("EVOLUTION_URL", "http://localhost:8080").rstrip("/")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "change-me-please")
EVOLUTION_WEBHOOK_URL = os.getenv(
    "EVOLUTION_WEBHOOK_URL",
    "http://host.docker.internal:8000/webhook",
)

DB_PATH = os.getenv("DB_PATH", "data/whatsapp_bot.db")

DEFAULT_SYSTEM_PROMPT = os.getenv(
    "DEFAULT_SYSTEM_PROMPT",
    "Você é um atendente virtual atencioso e útil. "
    "Responda de forma breve, clara e em português, com tom amigável.",
)

HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "20"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "800"))
