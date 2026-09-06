"""Unit tests for HistoricalContextStore and disaster precedent matching."""

import pytest

from malabar_watch.risk_engine.historical import HistoricalContextStore
from malabar_watch.risk_engine.models import RiskLevel


@pytest.fixture
def store() -> HistoricalContextStore:
    return HistoricalContextStore()


@pytest.mark.unit
def test_historical_dataset_loading(store: HistoricalContextStore) -> None:
    """Verify historical dataset loads all landmark disaster events."""
    events = store.get_all_events()
    assert len(events) >= 3

    event_ids = [e.event_id for e in events]
    assert "wayanad_2024" in event_ids
    assert "idukki_2020" in event_ids
    assert "kottayam_2021" in event_ids


@pytest.mark.unit
def test_suppression_for_low_and_moderate(store: HistoricalContextStore) -> None:
    """Historical precedent is suppressed (None) when risk is LOW or MODERATE."""
    assert store.find_precedent("wayanad", RiskLevel.LOW, 20.0) is None
    assert store.find_precedent("wayanad", RiskLevel.MODERATE, 75.0) is None


@pytest.mark.unit
def test_match_severe_wayanad(store: HistoricalContextStore) -> None:
    """Verify Wayanad SEVERE risk matches Chooralmala / Mundakkai 2024 precedent."""
    precedent = store.find_precedent("wayanad", RiskLevel.SEVERE, 350.0)
    assert precedent is not None
    assert precedent.event_id == "wayanad_2024"
    assert "Chooralmala" in precedent.location
    assert precedent.analog_threshold_level == "SEVERE"


@pytest.mark.unit
def test_match_high_kottayam(store: HistoricalContextStore) -> None:
    """Verify Kottayam HIGH risk matches Koottickal 2021 precedent."""
    precedent = store.find_precedent("kottayam", RiskLevel.HIGH, 180.0)
    assert precedent is not None
    assert precedent.event_id == "kottayam_2021"
    assert "Koottickal" in precedent.location
    assert precedent.analog_threshold_level == "HIGH"


@pytest.mark.unit
def test_micro_zone_prefix_normalization(store: HistoricalContextStore) -> None:
    """Micro-zones like 'kottayam_poonjar' and 'idukki_peerumade' resolve to parent district."""
    poonjar_match = store.find_precedent("kottayam_poonjar", RiskLevel.HIGH, 190.0)
    assert poonjar_match is not None
    assert poonjar_match.district == "kottayam"

    peerumade_match = store.find_precedent("idukki_peerumade", RiskLevel.SEVERE, 230.0)
    assert peerumade_match is not None
    assert peerumade_match.district == "idukki"


@pytest.mark.unit
def test_unknown_district_graceful_fallback(store: HistoricalContextStore) -> None:
    """Unknown or non-Western Ghats districts cleanly return None without crashing."""
    result = store.find_precedent("alappuzha", RiskLevel.SEVERE, 300.0)
    assert result is None
