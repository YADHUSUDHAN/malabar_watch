"""Dual-LLM gateway orchestrating Gemini -> Groq -> Template failover cascade."""

import logging
import time
from typing import TYPE_CHECKING, Any

from malabar_watch.llm.gemini import GeminiProvider
from malabar_watch.llm.groq import GroqProvider
from malabar_watch.llm.models import BilingualAdvisory, LLMProviderType
from malabar_watch.llm.templates import generate_template_advisory

if TYPE_CHECKING:
    from malabar_watch.risk_engine.models import RiskAssessment

logger = logging.getLogger(__name__)


class DualLLMGateway:
    """Resilient gateway providing zero-downtime bilingual early-warning advisory generation."""

    def __init__(
        self,
        gemini_provider: GeminiProvider | None = None,
        groq_provider: GroqProvider | None = None,
        gemini_key: str | None = None,
        groq_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.gemini_key = gemini_key
        self.groq_key = groq_key
        self.gemini = gemini_provider or GeminiProvider(api_key=gemini_key, timeout=timeout)
        self.groq = groq_provider or GroqProvider(api_key=groq_key, timeout=timeout)

    async def generate_advisory(self, assessment: "RiskAssessment") -> BilingualAdvisory:
        """Generates a structured bilingual advisory with resilient multi-provider failover.

        Failover Cascade:
        1. Primary: Google Gemini (gemini-2.5-flash)
        2. Fallback: Groq (llama-3.3-70b-versatile)
        3. Deterministic Safety Fallback: Rule-based template generator
        """
        overall_start = time.perf_counter()

        # Tier 1: Try Primary (Gemini)
        if self.gemini.is_available:
            try:
                start = time.perf_counter()
                data = await self.gemini.generate_advisory(assessment)
                latency = int((time.perf_counter() - start) * 1000)
                advisory = self._build_advisory(
                    data=data,
                    assessment=assessment,
                    provider=LLMProviderType.GEMINI,
                    latency_ms=latency,
                )
                logger.info("Bilingual advisory synthesized via Gemini in %sms", latency)
                return advisory
            except Exception as e:
                logger.warning("Primary LLM (Gemini) failed: %s. Initiating failover to Groq.", e)
        else:
            logger.info("Gemini credentials not available. Routing directly to Groq fallback.")

        # Tier 2: Try Fallback (Groq)
        if self.groq.is_available:
            try:
                start = time.perf_counter()
                data = await self.groq.generate_advisory(assessment)
                latency = int((time.perf_counter() - start) * 1000)
                advisory = self._build_advisory(
                    data=data,
                    assessment=assessment,
                    provider=LLMProviderType.GROQ,
                    latency_ms=latency,
                )
                logger.info("Bilingual advisory synthesized via Groq in %sms", latency)
                return advisory
            except Exception as e:
                logger.warning(
                    "Fallback LLM (Groq) failed: %s. Activating deterministic template fallback.",
                    e,
                )
        else:
            logger.info("Groq credentials not available. Falling back to offline template.")

        # Tier 3: Deterministic Rule-Based Template Engine (Zero Downtime Guarantee)
        total_latency = int((time.perf_counter() - overall_start) * 1000)
        logger.info("Activating deterministic rule-based template advisory generator.")
        return generate_template_advisory(assessment, latency_ms=total_latency)

    def _build_advisory(
        self,
        data: dict[str, Any],
        assessment: "RiskAssessment",
        provider: LLMProviderType,
        latency_ms: int,
    ) -> BilingualAdvisory:
        """Validates dictionary payload and constructs an immutable BilingualAdvisory model."""
        summary_en = str(data.get("summary_en", "")).strip()
        summary_ml = str(data.get("summary_ml", "")).strip()
        advisory_en = str(data.get("advisory_en", "")).strip()
        advisory_ml = str(data.get("advisory_ml", "")).strip()

        # Validate that all required text components are non-empty
        if not (summary_en and summary_ml and advisory_en and advisory_ml):
            raise ValueError(f"Incomplete advisory payload received from {provider.value}: {data}")

        return BilingualAdvisory(
            district_id=assessment.district,
            risk_level=assessment.risk_level,  # Strictly deterministic; never hallucinated
            summary_en=summary_en,
            summary_ml=summary_ml,
            advisory_en=advisory_en,
            advisory_ml=advisory_ml,
            provider_used=provider.value,
            latency_ms=latency_ms,
        )

    async def generate_bilingual_advisory(self, prompt: str) -> dict[str, str]:
        """Backward-compatibility interface for legacy callers."""
        from datetime import datetime

        from malabar_watch.risk_engine.models import EscalationState, RiskAssessment, RiskLevel

        synthetic_assessment = RiskAssessment(
            district="wayanad",
            assessed_at=datetime.now(),
            risk_level=RiskLevel.HIGH,
            escalation_state=EscalationState.FIRST_ASSESSMENT,
            rainfall_1h=15.0,
            rainfall_24h=140.0,
            rainfall_48h=180.0,
            rainfall_72h=210.0,
            antecedent_index=115.0,
            triggered_rules=[f"Prompt instruction: {prompt}"],
            requires_alert=True,
        )

        advisory = await self.generate_advisory(synthetic_assessment)
        return {
            "english": f"{advisory.summary_en} {advisory.advisory_en}",
            "malayalam": f"{advisory.summary_ml} {advisory.advisory_ml}",
            "provider_used": advisory.provider_used,
        }
