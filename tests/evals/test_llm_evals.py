"""LLM evaluation benchmark suite for bilingual advisory validation."""

import pytest

from malabar_watch.llm import DualLLMGateway


@pytest.mark.evals
@pytest.mark.asyncio
async def test_mock_gateway_bilingual_response() -> None:
    """Verify dual LLM gateway returns required bilingual response schema."""
    gateway = DualLLMGateway()
    response = await gateway.generate_bilingual_advisory("Generate Wayanad warning")

    assert "english" in response
    assert "malayalam" in response
    assert len(response["english"]) > 0
    assert len(response["malayalam"]) > 0
