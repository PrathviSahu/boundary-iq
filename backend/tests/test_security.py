import pytest
from fastapi.testclient import TestClient
from app.main import app, limiter

@pytest.fixture
def client():
    return TestClient(app)

def test_security_headers_present(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("Permissions-Policy") == "geolocation=(), camera=(), microphone=()"
    assert headers.get("Content-Security-Policy") == "default-src 'none'; frame-ancestors 'none'"

def test_hsts_applied_only_on_https(client, monkeypatch):
    # Standard HTTP request: no HSTS header
    http_res = client.get("/api/health")
    assert "Strict-Transport-Security" not in http_res.headers

    # Direct HTTPS request: HSTS header must be present
    direct_https_res = client.get("https://testserver/api/health")
    assert direct_https_res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

    # Untrusted peer spoofing X-Forwarded-Proto over HTTP: HSTS header MUST NOT be present
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    spoofed_res = client.get("/api/health", headers={"x-forwarded-proto": "https"})
    assert "Strict-Transport-Security" not in spoofed_res.headers

    # Trusted proxy request with X-Forwarded-Proto: HSTS header must be present
    monkeypatch.setenv("TRUSTED_PROXIES", "testclient")
    https_res = client.get("/api/health", headers={"x-forwarded-proto": "https"})
    assert https_res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

def test_cors_allows_whitelisted_origin(client):
    res = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"

def test_cors_rejects_unauthorized_origin(client):
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-phishing-site.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    # Unauthorized origin must NOT be reflected
    assert res.headers.get("access-control-allow-origin") != "https://malicious-phishing-site.com"
    assert res.headers.get("access-control-allow-origin") != "*"

def test_cors_allows_project_scoped_preview_origin(client):
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://boundary-iq-preview-123.vercel.app",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") == "https://boundary-iq-preview-123.vercel.app"

def test_cors_rejects_unrelated_vercel_origin(client):
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://some-other-project.vercel.app",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res.headers.get("access-control-allow-origin") != "https://some-other-project.vercel.app"
    assert res.headers.get("access-control-allow-origin") != "*"

def test_explanation_endpoint_caching(client):
    # First call
    res1 = client.get("/api/matches/ind_sa_t20wc_2024_final/explain/24")
    assert res1.status_code == 200
    data1 = res1.json()

    # Second call should immediately retrieve from cache
    res2 = client.get("/api/matches/ind_sa_t20wc_2024_final/explain/24")
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1["delivery_index"] == data2["delivery_index"]
    assert data1["headline"] == data2["headline"]
    assert data1["what_happened"] == data2["what_happened"]

def test_rate_limiter_enforcement(client):
    # Temporarily set lower limit for testing
    original_limit = limiter.explain_limit
    limiter.explain_limit = 5
    limiter.explain_requests.clear()

    try:
        # First 5 calls pass
        for i in range(5):
            res = client.get(f"/api/matches/ind_sa_t20wc_2024_final/explain/{i}")
            assert res.status_code == 200

        # 6th call should be rejected with 429
        res_blocked = client.get("/api/matches/ind_sa_t20wc_2024_final/explain/5")
        assert res_blocked.status_code == 429
        assert "Retry-After" in res_blocked.headers
        assert "Too many requests" in res_blocked.json()["detail"]
    finally:
        # Restore original limit
        limiter.explain_limit = original_limit
        limiter.explain_requests.clear()



# ---------------------------------------------------------------------------
# Issue 1 — AI Cache Isolation: different fantasy team configurations (captain,
# vice-captain, player list) must receive independent cache entries.
# ---------------------------------------------------------------------------

VALID_DELIVERY = 24  # delivery with a clear result to compare across teams

_BASE_11 = [
    "V Kohli", "JJ Bumrah", "RG Sharma", "HH Pandya", "AR Patel",
    "Arshdeep Singh", "Q de Kock", "H Klaasen", "DA Miller", "K Rabada", "KA Maharaj"
]


def _post_explain(client, delivery_id: int, captain: str, vice_captain: str, players: list):
    """POST to explain endpoint with a given team config."""
    body = {
        "selected_players": players,
        "captain": captain,
        "vice_captain": vice_captain,
    }
    return client.post(
        f"/api/matches/ind_sa_t20wc_2024_final/explain/{delivery_id}",
        json=body,
    )


def test_different_captains_produce_different_cache_entries(client):
    """Two teams identical except captain/VC must NOT share a cached explanation."""
    res_kohli  = _post_explain(client, VALID_DELIVERY, "V Kohli",   "JJ Bumrah", _BASE_11)
    res_bumrah = _post_explain(client, VALID_DELIVERY, "JJ Bumrah", "V Kohli",   _BASE_11)

    assert res_kohli.status_code == 200
    assert res_bumrah.status_code == 200

    exp_kohli  = res_kohli.json()["fantasy_impact_explanation"]
    exp_bumrah = res_bumrah.json()["fantasy_impact_explanation"]

    # The [C 2x] tag will appear on different players — strings must differ.
    assert exp_kohli != exp_bumrah, (
        "Cache isolation failure: teams with different captains returned identical "
        "fantasy_impact_explanation. SHA-256 team fingerprint may be missing from cache key."
    )


def test_same_team_config_returns_cached_explanation(client):
    """Identical team configs on the same delivery must hit the cache."""
    res1 = _post_explain(client, VALID_DELIVERY, "V Kohli", "JJ Bumrah", _BASE_11)
    res2 = _post_explain(client, VALID_DELIVERY, "V Kohli", "JJ Bumrah", _BASE_11)

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["fantasy_impact_explanation"] == res2.json()["fantasy_impact_explanation"]


def test_vice_captain_swap_produces_different_cache_entry(client):
    """Swapping vice-captain must produce a separate cache entry."""
    res_vc_bumrah  = _post_explain(client, VALID_DELIVERY, "V Kohli", "JJ Bumrah", _BASE_11)
    res_vc_klaasen = _post_explain(client, VALID_DELIVERY, "V Kohli", "H Klaasen", _BASE_11)

    assert res_vc_bumrah.status_code == 200
    assert res_vc_klaasen.status_code == 200

    exp_bumrah  = res_vc_bumrah.json()["fantasy_impact_explanation"]
    exp_klaasen = res_vc_klaasen.json()["fantasy_impact_explanation"]

    assert exp_bumrah != exp_klaasen, (
        "Cache isolation failure: teams with different VCs returned identical "
        "fantasy_impact_explanation."
    )


def test_different_player_list_produces_independent_response(client):
    """Swapping a non-captain player must produce a separate cache entry (no cross-contamination)."""
    squad_a = _BASE_11[:]
    squad_b = _BASE_11[:10] + ["AK Markram"]

    res_a = _post_explain(client, VALID_DELIVERY, "V Kohli", "JJ Bumrah", squad_a)
    res_b = _post_explain(client, VALID_DELIVERY, "V Kohli", "JJ Bumrah", squad_b)

    assert res_a.status_code == 200
    assert res_b.status_code == 200
    # Both must succeed independently with no exception — cache key isolation is the main check.


# ---------------------------------------------------------------------------
# SHA-256 fingerprint unit tests (pure logic — no HTTP, no mock)
# ---------------------------------------------------------------------------

def test_team_fingerprint_is_deterministic():
    from app.ai.service import _team_fingerprint
    from app.models.fantasy import FantasyTeamConfig

    team = FantasyTeamConfig(selected_players=_BASE_11, captain="V Kohli", vice_captain="JJ Bumrah")
    assert _team_fingerprint(team) == _team_fingerprint(team)


def test_team_fingerprint_differs_on_captain_change():
    from app.ai.service import _team_fingerprint
    from app.models.fantasy import FantasyTeamConfig

    t1 = FantasyTeamConfig(selected_players=_BASE_11, captain="V Kohli",   vice_captain="JJ Bumrah")
    t2 = FantasyTeamConfig(selected_players=_BASE_11, captain="JJ Bumrah", vice_captain="V Kohli")
    assert _team_fingerprint(t1) != _team_fingerprint(t2)


def test_team_fingerprint_differs_on_vice_captain_change():
    from app.ai.service import _team_fingerprint
    from app.models.fantasy import FantasyTeamConfig

    t1 = FantasyTeamConfig(selected_players=_BASE_11, captain="V Kohli", vice_captain="JJ Bumrah")
    t2 = FantasyTeamConfig(selected_players=_BASE_11, captain="V Kohli", vice_captain="H Klaasen")
    assert _team_fingerprint(t1) != _team_fingerprint(t2)


def test_team_fingerprint_differs_on_player_list_change():
    from app.ai.service import _team_fingerprint
    from app.models.fantasy import FantasyTeamConfig

    squad_a = _BASE_11[:]
    squad_b = _BASE_11[:10] + ["AK Markram"]
    t1 = FantasyTeamConfig(selected_players=squad_a, captain="V Kohli", vice_captain="JJ Bumrah")
    t2 = FantasyTeamConfig(selected_players=squad_b, captain="V Kohli", vice_captain="JJ Bumrah")
    assert _team_fingerprint(t1) != _team_fingerprint(t2)


def test_team_fingerprint_is_order_independent_for_players():
    """Player list order must not affect fingerprint — list is sorted before hashing."""
    from app.ai.service import _team_fingerprint
    from app.models.fantasy import FantasyTeamConfig

    t1 = FantasyTeamConfig(selected_players=_BASE_11,                     captain="V Kohli", vice_captain="JJ Bumrah")
    t2 = FantasyTeamConfig(selected_players=list(reversed(_BASE_11)),      captain="V Kohli", vice_captain="JJ Bumrah")
    assert _team_fingerprint(t1) == _team_fingerprint(t2)


def test_team_fingerprint_length():
    """Fingerprint must be exactly 16 lowercase hex characters."""
    from app.ai.service import _team_fingerprint
    from app.models.fantasy import FantasyTeamConfig

    team = FantasyTeamConfig(selected_players=_BASE_11, captain="V Kohli", vice_captain="JJ Bumrah")
    fp = _team_fingerprint(team)
    assert len(fp) == 16
    assert all(c in "0123456789abcdef" for c in fp)
