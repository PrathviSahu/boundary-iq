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
