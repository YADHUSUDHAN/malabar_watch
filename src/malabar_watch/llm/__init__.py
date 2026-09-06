"""LLM Gateway package supporting primary (Gemini), fallback (Groq), and template reasoning."""

from malabar_watch.llm.gateway import DualLLMGateway
from malabar_watch.llm.gemini import GeminiProvider
from malabar_watch.llm.groq import GroqProvider
from malabar_watch.llm.models import BilingualAdvisory, LLMProviderType
from malabar_watch.llm.templates import generate_template_advisory

__all__ = [
    "BilingualAdvisory",
    "DualLLMGateway",
    "GeminiProvider",
    "GroqProvider",
    "LLMProviderType",
    "generate_template_advisory",
]
