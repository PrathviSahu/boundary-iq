import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app"] == "BoundaryIQ"
    assert data["total_deliveries"] == 251

def test_matches_endpoint(client):
    res = client.get("/api/matches")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert "India" in data[0]["teams"]
    assert "South Africa" in data[0]["teams"]

def test_match_detail_endpoint(client):
    res = client.get("/api/matches/ind_sa_t20wc_2024_final")
    assert res.status_code == 200
    data = res.json()
    assert data["match_id"] == "ind_sa_t20wc_2024_final"
    assert "Kensington Oval" in data["venue"]

def test_snapshot_endpoint(client):
    res = client.get("/api/matches/ind_sa_t20wc_2024_final/snapshot/10")
    assert res.status_code == 200
    data = res.json()
    assert data["delivery_index"] == 10
    assert "striker" in data
    assert "bowler" in data
    assert "team_score" in data

def test_key_moments_endpoint(client):
    res = client.get("/api/matches/ind_sa_t20wc_2024_final/key-moments")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert any(km["category"] == "wicket" for km in data)

def test_players_endpoint(client):
    res = client.get("/api/matches/ind_sa_t20wc_2024_final/players")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 22
    names = [p["name"] for p in data]
    assert "V Kohli" in names
    assert "H Klaasen" in names

def test_ruleset_endpoint(client):
    res = client.get("/api/matches/ind_sa_t20wc_2024_final/ruleset")
    assert res.status_code == 200
    data = res.json()
    assert data["ruleset_id"] == "dream11_standard_t20_v2025"
    assert data["captain_multiplier"] == 2.0
    assert data["vice_captain_multiplier"] == 1.5
    assert data["wicket_normal"] == 30.0
    assert data["boundary_four_bonus"] == 4.0
    assert data["six_bonus"] == 6.0
    assert data["dot_ball_bowled"] == 1.0
    assert data["five_wicket_bonus"] == 12.0
    assert data["twenty_five_run_bonus"] == 4.0

def test_save_fantasy_team_endpoint(client):
    payload = {
        "team_id": "test_squad_1",
        "config": {
            "selected_players": [
                "V Kohli", "JJ Bumrah", "RG Sharma", "HH Pandya", "AR Patel", "Arshdeep Singh",
                "Q de Kock", "H Klaasen", "DA Miller", "K Rabada", "KA Maharaj"
            ],
            "captain": "V Kohli",
            "vice_captain": "JJ Bumrah"
        }
    }
    res = client.post("/api/fantasy/teams", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "saved"

def test_team_score_endpoint(client):
    res = client.get("/api/fantasy/teams/default/score?delivery_index=20")
    assert res.status_code == 200
    data = res.json()
    assert "player_scores" in data
    assert "ball_delta" in data
    assert data["team_total"] > 0

def test_explain_endpoint(client):
    res = client.get("/api/matches/ind_sa_t20wc_2024_final/explain/0")
    assert res.status_code == 200
    data = res.json()
    assert "what_happened" in data
    assert "why_it_matters" in data
    assert "cricket_rule" in data
    assert "evidence" in data
    assert "engine_source" in data
    assert len(data["evidence"]["grounded_in_data"]) > 0
    assert len(data["evidence"]["unavailable_evidence"]) > 0


# ---------------------------------------------------------------------------
# Issue 3 — Match ID validation: all match-scoped routes must return 404 for
# an unknown match_id.
# ---------------------------------------------------------------------------

VALID_ID = "ind_sa_t20wc_2024_final"
BAD_ID   = "non_existent_match_xyz"

def test_invalid_match_id_deliveries(client):
    """GET /matches/{match_id}/deliveries — unknown ID → 404."""
    res = client.get(f"/api/matches/{BAD_ID}/deliveries")
    assert res.status_code == 404
    assert BAD_ID in res.json()["detail"]

def test_invalid_match_id_snapshot(client):
    """GET /matches/{match_id}/snapshot/{idx} — unknown ID → 404."""
    res = client.get(f"/api/matches/{BAD_ID}/snapshot/0")
    assert res.status_code == 404

def test_invalid_match_id_key_moments(client):
    """GET /matches/{match_id}/key-moments — unknown ID → 404."""
    res = client.get(f"/api/matches/{BAD_ID}/key-moments")
    assert res.status_code == 404

def test_invalid_match_id_players(client):
    """GET /matches/{match_id}/players — unknown ID → 404."""
    res = client.get(f"/api/matches/{BAD_ID}/players")
    assert res.status_code == 404

def test_invalid_match_id_ruleset(client):
    """GET /matches/{match_id}/ruleset — unknown ID → 404."""
    res = client.get(f"/api/matches/{BAD_ID}/ruleset")
    assert res.status_code == 404

def test_invalid_match_id_explain_get(client):
    """GET /matches/{match_id}/explain/{id} — unknown ID → 404."""
    res = client.get(f"/api/matches/{BAD_ID}/explain/0")
    assert res.status_code == 404

def test_invalid_match_id_explain_post(client):
    """POST /matches/{match_id}/explain/{id} — unknown ID → 404."""
    res = client.post(f"/api/matches/{BAD_ID}/explain/0")
    assert res.status_code == 404

def test_valid_match_id_still_works(client):
    """Sanity: valid match_id continues to return 200 on affected routes."""
    assert client.get(f"/api/matches/{VALID_ID}/deliveries").status_code == 200
    assert client.get(f"/api/matches/{VALID_ID}/key-moments").status_code == 200
    assert client.get(f"/api/matches/{VALID_ID}/players").status_code == 200
    assert client.get(f"/api/matches/{VALID_ID}/ruleset").status_code == 200
    assert client.get(f"/api/matches/{VALID_ID}/explain/0").status_code == 200


# ---------------------------------------------------------------------------
# Issue 4 — Delivery index validation: negative and upper-bound values must
# be rejected with a 4xx response. Checks both the snapshot route (already
# had a check) and the GET team-score route (previously unguarded).
# ---------------------------------------------------------------------------

def test_negative_delivery_index_snapshot(client):
    res = client.get(f"/api/matches/{VALID_ID}/snapshot/-1")
    assert res.status_code == 400
    assert "out of range" in res.json()["detail"]

def test_upper_bound_delivery_index_snapshot(client):
    res = client.get(f"/api/matches/{VALID_ID}/snapshot/99999")
    assert res.status_code == 400
    assert "out of range" in res.json()["detail"]

def test_negative_delivery_index_team_score(client):
    """GET /fantasy/teams/score?delivery_index=-1 must return 400."""
    res = client.get("/api/fantasy/teams/default/score?delivery_index=-1")
    assert res.status_code == 400
    assert "out of range" in res.json()["detail"]

def test_upper_bound_delivery_index_team_score(client):
    """GET /fantasy/teams/score?delivery_index=99999 must return 400."""
    res = client.get("/api/fantasy/teams/default/score?delivery_index=99999")
    assert res.status_code == 400
    assert "out of range" in res.json()["detail"]

def test_negative_delivery_index_explain(client):
    res = client.get(f"/api/matches/{VALID_ID}/explain/-1")
    assert res.status_code == 400
    assert "out of range" in res.json()["detail"]

def test_upper_bound_delivery_index_explain(client):
    res = client.get(f"/api/matches/{VALID_ID}/explain/99999")
    assert res.status_code == 400
    assert "out of range" in res.json()["detail"]

def test_negative_delivery_index_custom_scores(client):
    res = client.post(f"/api/fantasy/scores/-1")
    assert res.status_code == 400
    assert "out of range" in res.json()["detail"]

def test_upper_bound_delivery_index_custom_scores(client):
    res = client.post(f"/api/fantasy/scores/99999")
    assert res.status_code == 400
    assert "out of range" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Issue 2 & 6 — Gemini timeout & admission saturation: _call_gemini must return
# None within (timeout + 0.5 s) when HTTP hangs, and fail-fast when saturated.
# ---------------------------------------------------------------------------

def test_gemini_timeout_returns_promptly(monkeypatch):
    """Hanging Gemini call must resolve in ≤ timeout + 0.5 s — not block on __exit__."""
    import time
    import threading
    import concurrent.futures as cf
    import app.main
    from app.api.routes import engine, DEFAULT_FANTASY_SQUAD
    from app.ai.service import AIExplanationService
    import app.ai.service as svc_module

    assert engine is not None, "Replay engine must be initialized"
    snapshot = engine.get_snapshot(0)
    delivery = snapshot.delivery_event
    _, impact, _, _ = engine.get_fantasy_scores_for_team(0, DEFAULT_FANTASY_SQUAD)

    # Use a real bounded executor for the test so we exercise the actual code path.
    hang_event = threading.Event()
    test_executor = cf.ThreadPoolExecutor(max_workers=2, thread_name_prefix="test_gemini")
    monkeypatch.setattr(svc_module, "_GEMINI_EXECUTOR", test_executor)

    svc = AIExplanationService()
    svc.api_key = "fake-key-for-timeout-test"

    # Fake Gemini client whose generate_content hangs indefinitely.
    class _HangingModels:
        @staticmethod
        def generate_content(**_kwargs):
            hang_event.wait(timeout=30)
            return None

    class _FakeClient:
        models = _HangingModels()

    svc.client = _FakeClient()

    timeout_val = 0.15  # 150 ms — fast enough for CI, longer than scheduler jitter
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", str(timeout_val))

    start = time.monotonic()
    result = svc._call_gemini(delivery, snapshot, impact, "2024.3.0")
    elapsed = time.monotonic() - start

    hang_event.set()                      # release the hanging thread for cleanup
    test_executor.shutdown(wait=False)    # don't block the test suite

    assert result is None, "Timed-out Gemini call must return None"
    assert elapsed < timeout_val + 0.5, (
        f"_call_gemini blocked for {elapsed:.2f}s after a {timeout_val}s timeout. "
        "The fix must not block on executor.__exit__; use concurrent.futures.wait() instead."
    )


def test_gemini_executor_saturation_fast_fails():
    """When all 4 semaphore slots are occupied, incoming requests must fail-fast without waiting."""
    import time
    import app.main
    from app.api.routes import engine, DEFAULT_FANTASY_SQUAD
    from app.ai.service import AIExplanationService, _GEMINI_SEMAPHORE

    assert engine is not None
    snapshot = engine.get_snapshot(0)
    delivery = snapshot.delivery_event
    _, impact, _, _ = engine.get_fantasy_scores_for_team(0, DEFAULT_FANTASY_SQUAD)

    svc = AIExplanationService()
    svc.api_key = "fake-key"
    svc.client = "active_stub"

    # Acquire all 4 slots manually to simulate saturation
    acquired_slots = []
    for _ in range(4):
        acquired_slots.append(_GEMINI_SEMAPHORE.acquire(blocking=False))
    assert all(acquired_slots), "Must acquire all 4 slots"

    try:
        # A 5th call must immediately return None without blocking
        start = time.monotonic()
        res = svc._call_gemini(delivery, snapshot, impact, "2024.3.0")
        elapsed = time.monotonic() - start
        assert res is None, "Saturated call must immediately return None"
        assert elapsed < 0.1, f"Saturated call must fail fast; took {elapsed:.2f}s"
    finally:
        # Release the 4 slots
        for _ in range(4):
            _GEMINI_SEMAPHORE.release()

    # Recovery: after slots are released, a new request can acquire a slot
    assert _GEMINI_SEMAPHORE.acquire(blocking=False) is True
    _GEMINI_SEMAPHORE.release()


def test_ai_cache_lru_capacity_and_eviction():
    """Cache must respect max_cache_size and evict least recently used entries."""
    from app.ai.service import AIExplanationService, _team_fingerprint
    from app.models.fantasy import FantasyTeamConfig
    from app.models.explanation import EventExplanation, RuleExplanation, EvidenceBoundary

    svc = AIExplanationService(max_cache_size=5)  # small size for testing
    team = FantasyTeamConfig(selected_players=["P" + str(i) for i in range(11)], captain="P0", vice_captain="P1")
    fp = _team_fingerprint(team)

    def _make_exp(idx: int):
        return EventExplanation(
            delivery_index=idx, over_display=f"0.{idx}", headline=f"H{idx}",
            what_happened="WH", simple_cricket_explanation="SC", why_it_matters="WM",
            fantasy_impact_explanation="FIE",
            cricket_rule=RuleExplanation(law_name="L", law_number="1", summary="S"),
            evidence=EvidenceBoundary(grounded_in_data=[], unavailable_evidence=[]),
            data_limitations=[], fan_takeaway="FT", engine_source="test"
        )

    # Insert 5 entries (0, 1, 2, 3, 4)
    for i in range(5):
        svc._put_in_cache(("match_1", i, "v1", fp), _make_exp(i))

    assert len(svc.cache) == 5
    assert ("match_1", 0, "v1", fp) in svc.cache

    # Access entry 0 so it becomes most recently used
    res0 = svc._get_from_cache(("match_1", 0, "v1", fp))
    assert res0 is not None

    # Insert entry 5 -> should evict entry 1 (least recently used, since entry 0 was accessed)
    svc._put_in_cache(("match_1", 5, "v1", fp), _make_exp(5))
    assert len(svc.cache) == 5
    assert ("match_1", 1, "v1", fp) not in svc.cache  # evicted!
    assert ("match_1", 0, "v1", fp) in svc.cache      # retained!
    assert ("match_1", 5, "v1", fp) in svc.cache      # new entry present!
