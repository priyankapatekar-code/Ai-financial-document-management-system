"""LLM access. Provider is chosen by LLM_PROVIDER in .env: "gemini" or "openrouter"."""
import httpx
from fastapi import HTTPException

from app import config

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_gemini_client = None
if config.LLM_PROVIDER == "gemini" and config.GEMINI_CONFIGURED:
    from google import genai
    _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)


def _generate_gemini(prompt: str) -> str:
    from google.genai import errors
    try:
        response = _gemini_client.models.generate_content(model=config.GEMINI_MODEL, contents=prompt)
    except errors.APIError as e:
        code = getattr(e, "code", None)
        if code == 429:
            raise HTTPException(429, "Gemini quota/rate limit reached. Please wait a bit and try again.")
        if code in (400, 401, 403):
            raise HTTPException(502, "Gemini rejected the request. Check that GEMINI_API_KEY is valid.")
        raise HTTPException(502, "Gemini is temporarily unavailable. Please try again.")
    except Exception:
        raise HTTPException(502, "Could not reach Gemini. Check your internet connection.")
    return response.text or "The model returned no answer."


def _generate_openrouter(prompt: str) -> str:
    try:
        r = httpx.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
            json={"model": config.OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}]},
            timeout=120,
        )
    except httpx.HTTPError:
        raise HTTPException(502, "Could not reach OpenRouter. Check your internet connection.")
    if r.status_code == 429:
        raise HTTPException(429, "OpenRouter rate limit reached (free models are limited). Please wait and try again.")
    if r.status_code in (400, 401, 402, 403, 404):
        raise HTTPException(502, "OpenRouter rejected the request. Check OPENROUTER_API_KEY and OPENROUTER_MODEL.")
    if r.status_code >= 400:
        raise HTTPException(502, "OpenRouter is temporarily unavailable. Please try again.")
    try:
        text = r.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(502, "OpenRouter returned an unexpected response. Try again or pick another model.")
    return text or "The model returned no answer."


def generate(prompt: str) -> str:
    if not config.LLM_CONFIGURED:
        key = "GEMINI_API_KEY" if config.LLM_PROVIDER == "gemini" else "OPENROUTER_API_KEY"
        raise HTTPException(503, f"AI is not configured: set {key} in .env and restart the server.")
    if config.LLM_PROVIDER == "openrouter":
        return _generate_openrouter(prompt)
    return _generate_gemini(prompt)
