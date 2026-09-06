"""Google Gemini LLM provider implementation for structured bilingual reasoning."""

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from google import genai
from google.genai import types

from malabar_watch.config import settings
from malabar_watch.llm.prompts import SYSTEM_PROMPT, build_advisory_prompt, sanitize_json_output

if TYPE_CHECKING:
    from malabar_watch.risk_engine.models import RiskAssessment

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Primary LLM provider using Google Gemini API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or "gemini-3.6-flash"
        self.timeout = timeout
        self._client: genai.Client | None = None

        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize Google Gemini client: %s", e)
                self._client = None

    @property
    def is_available(self) -> bool:
        """Checks whether Gemini credentials are configured."""
        return bool(self.api_key and self._client)

    async def generate_advisory(self, assessment: "RiskAssessment") -> dict[str, Any]:
        """Sends risk metrics prompt to Gemini and parses the structured JSON advisory."""
        if not self.is_available or self._client is None:
            raise RuntimeError("Gemini API key is not configured or client failed to initialize.")

        prompt = build_advisory_prompt(assessment)
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.2,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        async def _call() -> str:
            assert self._client is not None
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text or ""

        try:
            raw_text = await asyncio.wait_for(_call(), timeout=self.timeout)
            cleaned_json = sanitize_json_output(raw_text)
            data: dict[str, Any] = json.loads(cleaned_json)
            return data
        except TimeoutError as te:
            logger.warning("Gemini request timed out after %ss: %s", self.timeout, te)
            raise
        except Exception as e:
            logger.warning("Gemini generation failed: %s", e)
            raise
