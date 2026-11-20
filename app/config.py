"""Loads and validates configuration from the environment / .env file."""
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "8"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))

_PLACEHOLDERS = {"", "your_gemini_key", "your_api_key", "any_long_random_string", "your_secret_key"}


def _missing(value):
    return value is None or value.strip() in _PLACEHOLDERS


_problems = []
if _missing(SECRET_KEY):
    _problems.append("SECRET_KEY is missing (set a long random string)")
if _missing(ALGORITHM):
    _problems.append("ALGORITHM is missing (use HS256)")
if _problems:
    raise RuntimeError(
        "Configuration error in .env: " + "; ".join(_problems)
        + ". Copy .env.example to .env and fill in the values."
    )

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# Which LLM backend answers questions: "gemini" (default) or "openrouter".
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()
if LLM_PROVIDER not in ("gemini", "openrouter"):
    raise RuntimeError(f"Configuration error in .env: LLM_PROVIDER must be 'gemini' or 'openrouter', got '{LLM_PROVIDER}'.")

# The LLM key is only needed for AI answers, so the rest of the app can still start without it.
GEMINI_CONFIGURED = not _missing(GEMINI_API_KEY)
OPENROUTER_CONFIGURED = not _missing(OPENROUTER_API_KEY)
LLM_CONFIGURED = GEMINI_CONFIGURED if LLM_PROVIDER == "gemini" else OPENROUTER_CONFIGURED
if not LLM_CONFIGURED:
    _var = "GEMINI_API_KEY" if LLM_PROVIDER == "gemini" else "OPENROUTER_API_KEY"
    print(f"WARNING: LLM_PROVIDER={LLM_PROVIDER} but {_var} is not set - AI answers will be unavailable.")
