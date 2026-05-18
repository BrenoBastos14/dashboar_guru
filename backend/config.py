import os
from pathlib import Path

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


def _default_database_url() -> str:
    # SQLite local pra dev; em prod, DATABASE_URL aponta pro Postgres do Railway.
    db_path = os.getenv("DB_PATH", "data/whatsapp_bot.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


DATABASE_URL = os.getenv("DATABASE_URL") or _default_database_url()
# Railway publica DATABASE_URL como postgres:// — SQLAlchemy 2.0 só aceita postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DEFAULT_SYSTEM_PROMPT = os.getenv(
    "DEFAULT_SYSTEM_PROMPT",
    "Você é um atendente virtual atencioso e útil. "
    "Responda de forma breve, clara e em português, com tom amigável.",
)

HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "20"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "800"))

# Auth
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-please-this-is-not-safe")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", str(60 * 24 * 7)))

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
