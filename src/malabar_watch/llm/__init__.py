"""LLM Gateway package supporting primary (Gemini) and fallback (Groq) reasoning."""


class DualLLMGateway:
    """Resilient gateway that routes prompt requests to Google Gemini with failover to Groq."""

    def __init__(
        self,
        gemini_key: str | None = None,
        groq_key: str | None = None,
    ) -> None:
        self.gemini_key = gemini_key
        self.groq_key = groq_key

    async def generate_bilingual_advisory(self, prompt: str) -> dict[str, str]:
        """Placeholder method for bilingual (English + Malayalam) generation."""
        return {
            "english": "Bilingual advisory generator initialized.",
            "malayalam": "ദ്വിഭാഷാ മുന്നറിയിപ്പ് സംവിധാനം സജ്ജമാക്കി.",
            "provider_used": "mock",
        }
