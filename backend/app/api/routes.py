import os
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.models.match import MatchMetadata, Delivery, SnapshotState, KeyMoment, PlayerInfo
from app.models.fantasy import (
    RulesetConfig, PlayerFantasyScore, BallFantasyImpact,
    FantasyTeamConfig, FantasyScoreResponse, OptimalCaptaincyComparison
)
from app.models.explanation import EventExplanation
from app.replay.engine import ReplayEngine
from app.scoring.ruleset import DEFAULT_RULESET
from app.ai.service import AIExplanationService
from app.db.repository import DatabaseManager, DEFAULT_CONFIG

router = APIRouter()

# Default demo squad
DEFAULT_FANTASY_SQUAD = DEFAULT_CONFIG

# Database manager for persistent fantasy teams
db_manager: Optional[DatabaseManager] = None

# The Replay Engine and AI service will be attached to the router / app state
engine: Optional[ReplayEngine] = None
ai_service: Optional[AIExplanationService] = None

def init_api_services(
    replay_engine: ReplayEngine,
    explanation_svc: AIExplanationService,
    db: Optional[DatabaseManager] = None
):
    global engine, ai_service, db_manager
    engine = replay_engine
    ai_service = explanation_svc
    db_manager = db or DatabaseManager()


def _validate_match_id(match_id: str) -> None:
    """Raise HTTP 404 if match_id does not match the loaded match, or 500 if engine is absent."""
    if not engine:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    if engine.metadata.match_id != match_id:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")


def _validate_delivery_index(delivery_index: int) -> None:
    """Raise HTTP 400 for negative or out-of-range delivery indexes."""
    if not engine:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    if delivery_index < 0 or delivery_index >= len(engine.deliveries):
        raise HTTPException(
            status_code=400,
            detail=f"delivery_index {delivery_index} is out of range "
                   f"(valid: 0–{len(engine.deliveries) - 1})"
        )

def _get_db() -> DatabaseManager:
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

@router.get("/health")
def health_check():
    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    db_ok = _get_db().check_health()
    return {
        "status": "healthy" if db_ok and engine else "degraded",
        "app": "BoundaryIQ",
        "version": "1.0.0",
        "database_connected": db_ok,
        "gemini_ai_enabled": has_gemini,
        "gemini_model": model_name,
        "match_id": engine.metadata.match_id if engine else None,
        "match_name": engine.metadata.event_name if engine else None,
        "total_deliveries": len(engine.deliveries) if engine else 0
    }

@router.get("/ready")
def readiness_check():
    db_ok = _get_db().check_health()
    engine_ok = bool(engine and engine.metadata and len(engine.deliveries) > 0)
    if not (db_ok and engine_ok):
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "database": db_ok, "engine": engine_ok}
        )
    return {"status": "ready", "database": "healthy", "engine": "loaded", "deliveries": len(engine.deliveries)}

@router.get("/matches")
def get_matches():
    if not engine:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    return [engine.metadata]

@router.get("/matches/{match_id}", response_model=MatchMetadata)
def get_match(match_id: str):
    if not engine or engine.metadata.match_id != match_id:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")
    return engine.metadata

@router.get("/matches/{match_id}/deliveries", response_model=List[Delivery])
def get_deliveries(match_id: str):
    _validate_match_id(match_id)
    return engine.deliveries

@router.get("/matches/{match_id}/snapshot/{delivery_index}", response_model=SnapshotState)
def get_snapshot(match_id: str, delivery_index: int):
    _validate_match_id(match_id)
    _validate_delivery_index(delivery_index)
    return engine.get_snapshot(delivery_index)

@router.get("/matches/{match_id}/key-moments", response_model=List[KeyMoment])
def get_key_moments(match_id: str, filter_type: Optional[str] = Query(None, alias="category")):
    _validate_match_id(match_id)
    return engine.get_key_moments(filter_type)

@router.get("/matches/{match_id}/players", response_model=List[PlayerInfo])
def get_players(match_id: str):
    _validate_match_id(match_id)
    return engine.metadata.roster

@router.get("/matches/{match_id}/ruleset", response_model=RulesetConfig)
def get_ruleset(match_id: str):
    _validate_match_id(match_id)
    return engine.ruleset

# --- Fantasy Endpoints ---

class TeamCreationRequest(BaseModel):
    team_id: str = "custom_team"
    config: FantasyTeamConfig

@router.post("/fantasy/teams")
def save_fantasy_team(req: TeamCreationRequest):
    if len(req.config.selected_players) != 11:
        raise HTTPException(status_code=400, detail="Fantasy squad must contain exactly 11 players")
    if not req.config.captain or req.config.captain not in req.config.selected_players:
        raise HTTPException(status_code=400, detail="Captain must be in the selected 11")
    if not req.config.vice_captain or req.config.vice_captain not in req.config.selected_players:
        raise HTTPException(status_code=400, detail="Vice-Captain must be in the selected 11")
    if req.config.captain == req.config.vice_captain:
        raise HTTPException(status_code=400, detail="Captain and Vice-Captain must be different")

    _get_db().save_team(req.team_id, req.config)
    return {"status": "saved", "team_id": req.team_id, "config": req.config}

@router.get("/fantasy/teams")
def list_fantasy_teams():
    return _get_db().list_teams()

@router.get("/fantasy/teams/{team_id}")
def get_fantasy_team(team_id: str):
    team = _get_db().get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")
    return {"team_id": team_id, "config": team}

@router.get("/fantasy/teams/{team_id}/score", response_model=FantasyScoreResponse)
def get_team_score(team_id: str, delivery_index: int = Query(0)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not ready")
    _validate_delivery_index(delivery_index)
    team = _get_db().get_team(team_id) or DEFAULT_FANTASY_SQUAD
    squad_scores, ball_delta, team_total, team_delta = engine.get_fantasy_scores_for_team(
        delivery_index, team
    )
    dlv = engine.deliveries[delivery_index] if delivery_index < len(engine.deliveries) else None
    optimal_c = engine.get_optimal_captaincy(delivery_index, team)
    return FantasyScoreResponse(
        delivery_index=delivery_index,
        over_display=dlv.over_display if dlv else "0.0",
        player_scores=squad_scores,
        ball_delta=ball_delta,
        team_total=team_total,
        team_delta=team_delta,
        optimal_captaincy=optimal_c
    )

@router.post("/fantasy/scores/{delivery_index}", response_model=FantasyScoreResponse)
def compute_custom_scores(delivery_index: int, team_config: Optional[FantasyTeamConfig] = None):
    _validate_delivery_index(delivery_index)

    team = team_config or DEFAULT_FANTASY_SQUAD
    squad_scores, ball_delta, team_total, team_delta = engine.get_fantasy_scores_for_team(
        delivery_index, team
    )
    dlv = engine.deliveries[delivery_index]
    optimal_c = engine.get_optimal_captaincy(delivery_index, team)
    return FantasyScoreResponse(
        delivery_index=delivery_index,
        over_display=dlv.over_display,
        player_scores=squad_scores,
        ball_delta=ball_delta,
        team_total=team_total,
        team_delta=team_delta,
        optimal_captaincy=optimal_c
    )

# --- AI & Match Event Explainer Endpoints ---

@router.get("/matches/{match_id}/explain/{delivery_id}", response_model=EventExplanation)
def explain_event_get(match_id: str, delivery_id: int):
    _validate_match_id(match_id)
    return _explain_internal(delivery_id, DEFAULT_FANTASY_SQUAD)

@router.post("/matches/{match_id}/explain/{delivery_id}", response_model=EventExplanation)
def explain_event_post(match_id: str, delivery_id: int, team_config: Optional[FantasyTeamConfig] = None):
    _validate_match_id(match_id)
    team = team_config or DEFAULT_FANTASY_SQUAD
    return _explain_internal(delivery_id, team)

def _explain_internal(delivery_id: int, team: FantasyTeamConfig) -> EventExplanation:
    if not engine or not ai_service:
        raise HTTPException(status_code=500, detail="Services not initialized")
    _validate_delivery_index(delivery_id)

    snapshot = engine.get_snapshot(delivery_id)
    delivery = snapshot.delivery_event
    _, ball_delta, _, _ = engine.get_fantasy_scores_for_team(delivery_id, team)

    return ai_service.explain_delivery(
        match_id=engine.metadata.match_id,
        delivery=delivery,
        snapshot=snapshot,
        fantasy_impact=ball_delta,
        team_config=team,
        ruleset_version=engine.ruleset.version
    )

