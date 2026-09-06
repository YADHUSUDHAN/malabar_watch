"""Unit tests for subscriber and alert log storage operations in DatabaseManager."""

import pytest
from malabar_watch.storage import DatabaseManager


@pytest.fixture
def db():
    """In-memory SQLite database for testing."""
    manager = DatabaseManager(db_path=":memory:")
    manager.initialize_schema()
    return manager


def test_add_and_get_subscriber(db):
    # Add new subscriber
    added = db.add_subscriber(chat_id=12345, district_id="wayanad")
    assert added is True

    sub = db.get_subscriber(12345)
    assert sub is not None
    assert sub["chat_id"] == 12345
    assert sub["district_id"] == "wayanad"
    assert sub["is_active"] == 1


def test_update_existing_subscriber(db):
    db.add_subscriber(chat_id=12345, district_id="wayanad")
    # Change to idukki
    db.add_subscriber(chat_id=12345, district_id="idukki")

    sub = db.get_subscriber(12345)
    assert sub["district_id"] == "idukki"
    assert sub["is_active"] == 1


def test_remove_subscriber(db):
    db.add_subscriber(chat_id=12345, district_id="all")
    removed = db.remove_subscriber(12345)
    assert removed is True

    sub = db.get_subscriber(12345)
    assert sub["is_active"] == 0

    # Removing again should return False since already inactive
    assert db.remove_subscriber(12345) is False


def test_get_subscribers_filtering(db):
    db.add_subscriber(chat_id=1, district_id="wayanad")
    db.add_subscriber(chat_id=2, district_id="idukki")
    db.add_subscriber(chat_id=3, district_id="all")
    db.add_subscriber(chat_id=4, district_id="wayanad")
    db.remove_subscriber(4)  # Inactive

    # Filter for wayanad (should include chat 1 and chat 3 'all', excluding inactive chat 4)
    wayanad_subs = db.get_subscribers("wayanad")
    assert {s["chat_id"] for s in wayanad_subs} == {1, 3}

    # Filter for idukki (should include chat 2 and chat 3 'all')
    idukki_subs = db.get_subscribers("idukki")
    assert {s["chat_id"] for s in idukki_subs} == {2, 3}

    # Filter for kottayam (only chat 3 'all')
    kottayam_subs = db.get_subscribers("kottayam")
    assert {s["chat_id"] for s in kottayam_subs} == {3}

    # All active subscribers
    all_active = db.get_subscribers()
    assert {s["chat_id"] for s in all_active} == {1, 2, 3}


def test_log_alert_dispatch(db):
    log_id = db.log_alert_dispatch(
        district_id="wayanad",
        risk_level="SEVERE",
        assessment_id=42,
        delivered_count=10,
        failed_count=1,
    )
    assert log_id > 0
