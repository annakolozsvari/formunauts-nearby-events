import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE_COORDS    = "SRID=4326;POINT (16.374211 48.225678)"
NEARBY_COORDS  = "SRID=4326;POINT (16.350123 48.209845)"  # ~2.4 km from base
FAR_COORDS     = "SRID=4326;POINT (17.0 47.8)"            # ~62 km from base
INVALID_COORDS = "not-a-point"


def make_event(pk, coords, timestamp):
    return {
        "model": "tracking.event",
        "pk": pk,
        "fields": {
            "customer": 1,
            "fundraiser": 1,
            "name": "test-event",
            "event_type": "automatic",
            "timestamp": timestamp,
            "event_context": {"source_id": "s", "source_category": "c"},
            "browser_location": {
                "current": "https://example.com/",
                "referrer": "https://example.com/",
            },
            "device_coordinates": coords,
        },
    }


EVENTS = [
    make_event(1, BASE_COORDS,   "2026-03-01T10:00:00Z"),  # base event
    make_event(2, NEARBY_COORDS, "2026-03-01T11:00:00Z"),  # nearby, same date
    make_event(3, FAR_COORDS,    "2026-03-01T12:00:00Z"),  # far, same date
    make_event(4, NEARBY_COORDS, "2026-03-02T10:00:00Z"),  # nearby, different date
]


@pytest.fixture(autouse=True)
def mock_input():
    with patch("pathlib.Path.read_text", return_value=json.dumps(EVENTS)):
        yield


# --- radius filtering ---

def test_returns_nearby_events():
    res = client.get("/events/1/nearby_events?radius=5000")
    assert res.status_code == 200
    pks = [e["pk"] for e in res.json()]
    assert 2 in pks

def test_excludes_far_events():
    res = client.get("/events/1/nearby_events?radius=5000")
    pks = [e["pk"] for e in res.json()]
    assert 3 not in pks

def test_excludes_base_event_from_results():
    res = client.get("/events/1/nearby_events?radius=5000")
    pks = [e["pk"] for e in res.json()]
    assert 1 not in pks

def test_radius_zero_returns_empty():
    res = client.get("/events/1/nearby_events?radius=0")
    assert res.status_code == 200
    assert res.json() == []


# --- date filter ---

def test_date_filter_includes_matching_date():
    res = client.get("/events/1/nearby_events?radius=5000&date=2026-03-01")
    pks = [e["pk"] for e in res.json()]
    assert 2 in pks

def test_date_filter_excludes_other_dates():
    res = client.get("/events/1/nearby_events?radius=5000&date=2026-03-01")
    pks = [e["pk"] for e in res.json()]
    assert 4 not in pks

def test_no_date_filter_returns_all_nearby():
    res = client.get("/events/1/nearby_events?radius=5000")
    pks = [e["pk"] for e in res.json()]
    assert 2 in pks
    assert 4 in pks


# --- error cases ---

def test_unknown_event_id_returns_404():
    res = client.get("/events/9999/nearby_events?radius=5000")
    assert res.status_code == 404

def test_missing_radius_returns_422():
    res = client.get("/events/1/nearby_events")
    assert res.status_code == 422

def test_negative_radius_returns_422():
    res = client.get("/events/1/nearby_events?radius=-1")
    assert res.status_code == 422

def test_invalid_base_geolocation_returns_400():
    events = [
        make_event(1, INVALID_COORDS, "2026-03-01T10:00:00Z"),
        make_event(2, NEARBY_COORDS,  "2026-03-01T11:00:00Z"),
    ]
    with patch("pathlib.Path.read_text", return_value=json.dumps(events)):
        res = client.get("/events/1/nearby_events?radius=5000")
    assert res.status_code == 400

def test_invalid_nearby_geolocation_returns_400():
    events = [
        make_event(1, BASE_COORDS,    "2026-03-01T10:00:00Z"),
        make_event(2, INVALID_COORDS, "2026-03-01T11:00:00Z"),
    ]
    with patch("pathlib.Path.read_text", return_value=json.dumps(events)):
        res = client.get("/events/1/nearby_events?radius=5000")
    assert res.status_code == 400


# --- response shape ---

def test_response_excludes_model_field():
    res = client.get("/events/1/nearby_events?radius=5000")
    assert res.status_code == 200
    for event in res.json():
        assert "model" not in event

def test_response_includes_pk():
    res = client.get("/events/1/nearby_events?radius=5000")
    for event in res.json():
        assert "pk" in event
