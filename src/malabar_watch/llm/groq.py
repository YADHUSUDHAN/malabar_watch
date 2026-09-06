"""Groq LLM provider implementation for ultra-fast fallback bilingual reasoning."""

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from groq import AsyncGroq

from malabar_watch.config import settings
from malabar_watch.llm.prompts import SYSTEM_PROMPT, build_advisory_prompt, sanitize_json_output

if TYPE_CHECKING:
    from malabar_watch.risk_engine.models import RiskAssessment

logger = logging.getLogger(__name__)


class GroqProvider:
    """Fallback LLM provider using Groq Cloud API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        self.timeout = timeout
        self._client: AsyncGroq | None = None

        if self.api_key:
            try:
                self._client = AsyncGroq(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize Groq client: %s", e)
                self._client = None

    @property
    def is_available(self) -> bool:
        """Checks whether Groq credentials are configured."""
        return bool(self.api_key and self._client)

    async def generate_advisory(self, assessment: "RiskAssessment") -> dict[str, Any]:
        """Sends risk metrics prompt to Groq and parses the structured JSON advisory."""
        if not self.is_available or self._client is None:
            raise RuntimeError("Groq API key is not configured or client failed to initialize.")

        prompt = build_advisory_prompt(assessment)

        async def _call() -> str:
            assert self._client is not None
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            choice = response.choices[0]
            return choice.message.content or ""

        try:
            raw_text = await asyncio.wait_for(_call(), timeout=self.timeout)
            cleaned_json = sanitize_json_output(raw_text)
            data: dict[str, Any] = json.loads(cleaned_json)
            return data
        except TimeoutError as te:
            logger.warning("Groq request timed out after %ss: %s", self.timeout, te)
            raise
        except Exception as e:
            logger.warning("Groq generation failed: %s", e)
            raise
