import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.models.fantasy import FantasyTeamConfig
from app.db.repository import DatabaseManager

client = TestClient(app)

MATCH_ID = "ind_sa_t20wc_2024_final"


def test_sqlite_persistence_across_restart():
    """Verify that fantasy teams persist in SQLite across repository restarts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = os.path.join(tmpdir, "test_boundary.db")
        
        # Instance 1: create and save a team
        db1 = DatabaseManager(db_file)
        test_team = FantasyTeamConfig(
            selected_players=[
                "V Kohli", "JJ Bumrah", "RG Sharma", "HH Pandya", "AR Patel",
                "Arshdeep Singh", "Q de Kock", "H Klaasen", "DA Miller", "K Rabada", "KA Maharaj"
            ],
            captain="JJ Bumrah",
            vice_captain="V Kohli"
        )
        db1.save_team("user_saved_1", test_team, name="My Champions XI")
        
        # Instance 2 (simulating cold server restart)
        db2 = DatabaseManager(db_file)
        retrieved = db2.get_team("user_saved_1")
        
        assert retrieved is not None
        assert retrieved.captain == "JJ Bumrah"
        assert retrieved.vice_captain == "V Kohli"
        assert len(retrieved.selected_players) == 11
        assert "HH Pandya" in retrieved.selected_players


def test_readiness_endpoint():
    """Verify /api/ready reports healthy status for both engine and database."""
    response = client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "healthy"
    assert data["engine"] == "loaded"
    assert data["deliveries"] > 0


def test_health_endpoint_includes_database():
    """Verify /api/health includes database connection status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True


def test_payload_size_limit_rejection():
    """Verify payloads exceeding 100 KB are rejected with HTTP 413."""
    # Create large dummy payload
    oversized_data = "a" * (105 * 1024)
    response = client.post(
        f"/api/fantasy/scores/1",
        content=oversized_data,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert "Payload too large" in response.json()["detail"]


def test_optimal_captaincy_calculation():
    """Verify that optimal captaincy comparison is computed accurately on delivery 118 (Kohli 76)."""
    # Kohli scored 76 runs, while Axar scored 47
    payload = {
        "selected_players": [
            "V Kohli", "JJ Bumrah", "RG Sharma", "HH Pandya", "AR Patel",
            "Arshdeep Singh", "Q de Kock", "H Klaasen", "DA Miller", "K Rabada", "KA Maharaj"
        ],
        "captain": "RG Sharma",       # Sharma scored 9 runs (low)
        "vice_captain": "HH Pandya"   # Pandya didn't bat yet in Innings 1
    }
    
    response = client.post(f"/api/fantasy/scores/118", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "optimal_captaincy" in data
    opt = data["optimal_captaincy"]
    assert opt is not None
    assert opt["optimal_captain"] == "V Kohli"
    assert opt["point_difference"] > 0
    assert opt["is_already_optimal"] is False
    assert "Alternative" in opt["summary"] or "What-If" in opt["summary"]


def test_optimal_captaincy_already_optimal():
    """Verify that when optimal C & VC are already picked, is_already_optimal is True."""
    payload = {
        "selected_players": [
            "V Kohli", "JJ Bumrah", "RG Sharma", "HH Pandya", "AR Patel",
            "Arshdeep Singh", "Q de Kock", "H Klaasen", "DA Miller", "K Rabada", "KA Maharaj"
        ],
        "captain": "V Kohli",        # Kohli is top scorer at ball 118
        "vice_captain": "AR Patel"   # Axar is 2nd top scorer at ball 118
    }
    
    response = client.post(f"/api/fantasy/scores/118", json=payload)
    assert response.status_code == 200
    opt = response.json()["optimal_captaincy"]
    assert opt is not None
    assert opt["optimal_captain"] == "V Kohli"
    assert opt["optimal_vice_captain"] == "AR Patel"
    assert opt["point_difference"] == 0.0
    assert opt["is_already_optimal"] is True
    assert "Peak Captaincy" in opt["summary"]


def test_curated_key_moment_explanation():
    """Verify that iconic delivery 244 (Suryakumar catch) returns rich curated context in deterministic fallback."""
    from app.main import ai_service, replay_engine
    from app.db.repository import DEFAULT_CONFIG
    snap = replay_engine.get_snapshot(244)
    _, delta, _, _ = replay_engine.get_fantasy_scores_for_team(244, DEFAULT_CONFIG)
    
    # Test deterministic fallback specifically
    explanation = ai_service._generate_deterministic_explanation(snap.delivery_event, snap, delta)
    assert "CATCH OF THE CENTURY" in explanation.headline
    assert "Suryakumar" in explanation.what_happened
    assert len(explanation.next_ball_watchout) > 0
    assert "16 runs needed" in explanation.next_ball_watchout
