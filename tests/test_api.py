import pytest
from fastapi.testclient import TestClient

from stargaze.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_sky_endpoint_returns_valid_shape(client):
    resp = client.get("/api/sky", params={"lat": 51.4769, "lon": 0.0})
    assert resp.status_code == 200
    body = resp.json()

    assert body["observer"]["lat"] == 51.4769
    assert len(body["stars"]) > 0
    for star in body["stars"]:
        assert -90 <= star["alt"] <= 90
        assert 0 <= star["az"] < 360

    assert len(body["planets"]) == 7
    for planet in body["planets"]:
        assert -90 <= planet["alt"] <= 90
        assert 0 <= planet["az"] < 360

    assert -90 <= body["sun"]["alt"] <= 90
    assert -90 <= body["moon"]["alt"] <= 90
    assert 0 <= body["moon"]["illuminated_fraction"] <= 1

    assert len(body["constellations"]) == 88
    orion = next(c for c in body["constellations"] if c["abbr"] == "Ori")
    assert orion["name"] == "Orion"
    assert len(orion["lines"]) > 0
    for line in orion["lines"]:
        assert len(line) >= 2


def test_sky_endpoint_respects_magnitude_limit(client):
    dim = client.get("/api/sky", params={"lat": 51.4769, "lon": 0.0, "mag_limit": 2.0}).json()
    bright_count = len(dim["stars"])
    default = client.get("/api/sky", params={"lat": 51.4769, "lon": 0.0}).json()
    default_count = len(default["stars"])
    assert bright_count < default_count
    assert all(s["mag"] <= 2.0 for s in dim["stars"])


def test_sky_endpoint_accepts_explicit_time(client):
    resp = client.get(
        "/api/sky",
        params={"lat": 51.4769, "lon": 0.0, "time": "2026-03-20T12:00:00Z"},
    )
    assert resp.status_code == 200
    assert resp.json()["observer"]["time"].startswith("2026-03-20T12:00:00")


def test_sky_endpoint_requires_lat_lon(client):
    resp = client.get("/api/sky")
    assert resp.status_code == 422


def test_sky_endpoint_rejects_out_of_range_lat(client):
    resp = client.get("/api/sky", params={"lat": 200.0, "lon": 0.0})
    assert resp.status_code == 422
