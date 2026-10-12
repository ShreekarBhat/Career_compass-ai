"""Thin Groq wrapper. Every call degrades gracefully: callers always have a deterministic fallback."""
import json
import logging
import re

from app.core.config import settings
from app.core.sanitize import UNTRUSTED_NOTICE

logger = logging.getLogger(__name__)


class LLM:
    def __init__(self) -> None:
        self._client = None

    @property
    def available(self) -> bool:
        return bool(settings.groq_api_key)

    def _get_client(self):
        if self._client is None:
            from groq import Groq

            self._client = Groq(api_key=settings.groq_api_key, timeout=30.0, max_retries=1)
        return self._client

    def chat(self, system: str, user: str, temperature: float = 0.3, max_tokens: int = 900,
             json_mode: bool = False) -> str | None:
        if not self.available:
            return None
        try:
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = self._get_client().chat.completions.create(
                model=settings.groq_model,
                messages=[{"role": "system", "content": f"{system}\n\n{UNTRUSTED_NOTICE}"},
                          {"role": "user", "content": user}],
                temperature=temperature, max_tokens=max_tokens, **kwargs)
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("LLM call failed: %s", exc)
            return None

    def json(self, system: str, user: str, max_tokens: int = 1200, temperature: float = 0.2) -> dict | list | None:
        raw = self.chat(system + "\nRespond with valid JSON only.", user, temperature, max_tokens, json_mode=True)
        return parse_json(raw)


def parse_json(raw: str | None):
    if not raw:
        return None
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"[\{\[].*[\}\]]", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


llm = LLM()
