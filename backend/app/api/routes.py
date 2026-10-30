import os
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.models.match import MatchMetadata, Delivery, SnapshotState, KeyMoment, PlayerInfo
from app.models.fantasy import (
    RulesetConfig, PlayerFantasyScore, BallFantasyImpact,
    FantasyTeamConfig, FantasyScoreResponse
)
from app.models.explanation import EventExplanation
from app.replay.engine import ReplayEngine
from app.scoring.ruleset import DEFAULT_RULESET
from app.ai.service import AIExplanationService

router = APIRouter()

# Default demo squad
DEFAULT_FANTASY_SQUAD = FantasyTeamConfig(
    selected_players=[
        "V Kohli",
        "JJ Bumrah",
        "RG Sharma",
        "HH Pandya",
        "AR Patel",
        "Arshdeep Singh",
        "Q de Kock",
        "H Klaasen",
        "DA Miller",
        "K Rabada",
        "KA Maharaj"
    ],
    captain="V Kohli",
    vice_captain="JJ Bumrah"
)

# User-saved fantasy teams store (in-memory for MVP)
saved_fantasy_teams: Dict[str, FantasyTeamConfig] = {
    "default": DEFAULT_FANTASY_SQUAD,
    "demo_team_1": DEFAULT_FANTASY_SQUAD
}

# The Replay Engine and AI service will be attached to the router / app state
engine: Optional[ReplayEngine] = None
ai_service: Optional[AIExplanationService] = None

def init_api_services(replay_engine: ReplayEngine, explanation_svc: AIExplanationService):
    global engine, ai_service
    engine = replay_engine
    ai_service = explanation_svc

@router.get("/health")
def health_check():
    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    return {
        "status": "healthy",
        "app": "BoundaryIQ",
        "version": "1.0.0",
        "gemini_ai_enabled": has_gemini,
        "gemini_model": model_name,
        "match_id": engine.metadata.match_id if engine else None,
        "match_name": engine.metadata.event_name if engine else None,
        "total_deliveries": len(engine.deliveries) if engine else 0
    }

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
    if not engine:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    return engine.deliveries

@router.get("/matches/{match_id}/snapshot/{delivery_index}", response_model=SnapshotState)
def get_snapshot(match_id: str, delivery_index: int):
    if not engine:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    if delivery_index < 0 or delivery_index >= len(engine.deliveries):
        raise HTTPException(status_code=404, detail="Delivery index out of bounds")
    return engine.get_snapshot(delivery_index)

@router.get("/matches/{match_id}/key-moments", response_model=List[KeyMoment])
def get_key_moments(match_id: str, filter_type: Optional[str] = Query(None, alias="category")):
    if not engine:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    return engine.get_key_moments(filter_type)

@router.get("/matches/{match_id}/players", response_model=List[PlayerInfo])
def get_players(match_id: str):
    if not engine:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    return engine.metadata.roster

@router.get("/matches/{match_id}/ruleset", response_model=RulesetConfig)
def get_ruleset(match_id: str):
    if not engine:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
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

    saved_fantasy_teams[req.team_id] = req.config
    return {"status": "saved", "team_id": req.team_id, "config": req.config}

@router.get("/fantasy/teams/{team_id}/score")
def get_team_score(team_id: str, delivery_index: int = Query(0)):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not ready")
    team = saved_fantasy_teams.get(team_id, DEFAULT_FANTASY_SQUAD)
    squad_scores, ball_delta, team_total, team_delta = engine.get_fantasy_scores_for_team(
        delivery_index, team
    )
    dlv = engine.deliveries[delivery_index] if delivery_index < len(engine.deliveries) else None
    return FantasyScoreResponse(
        delivery_index=delivery_index,
        over_display=dlv.over_display if dlv else "0.0",
        player_scores=squad_scores,
        ball_delta=ball_delta,
        team_total=team_total,
        team_delta=team_delta
    )

@router.post("/fantasy/scores/{delivery_index}", response_model=FantasyScoreResponse)
def compute_custom_scores(delivery_index: int, team_config: Optional[FantasyTeamConfig] = None):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not ready")
    if delivery_index < 0 or delivery_index >= len(engine.deliveries):
        raise HTTPException(status_code=404, detail="Delivery index out of bounds")

    team = team_config or DEFAULT_FANTASY_SQUAD
    squad_scores, ball_delta, team_total, team_delta = engine.get_fantasy_scores_for_team(
        delivery_index, team
    )
    dlv = engine.deliveries[delivery_index]
    return FantasyScoreResponse(
        delivery_index=delivery_index,
        over_display=dlv.over_display,
        player_scores=squad_scores,
        ball_delta=ball_delta,
        team_total=team_total,
        team_delta=team_delta
    )

# --- AI & Match Event Explainer Endpoints ---

@router.get("/matches/{match_id}/explain/{delivery_id}", response_model=EventExplanation)
def explain_event_get(match_id: str, delivery_id: int):
    return _explain_internal(delivery_id, DEFAULT_FANTASY_SQUAD)

@router.post("/matches/{match_id}/explain/{delivery_id}", response_model=EventExplanation)
def explain_event_post(match_id: str, delivery_id: int, team_config: Optional[FantasyTeamConfig] = None):
    team = team_config or DEFAULT_FANTASY_SQUAD
    return _explain_internal(delivery_id, team)

def _explain_internal(delivery_id: int, team: FantasyTeamConfig) -> EventExplanation:
    if not engine or not ai_service:
        raise HTTPException(status_code=500, detail="Services not initialized")
    if delivery_id < 0 or delivery_id >= len(engine.deliveries):
        raise HTTPException(status_code=404, detail="Delivery index out of bounds")

    snapshot = engine.get_snapshot(delivery_id)
    delivery = snapshot.delivery_event
    _, ball_delta, _, _ = engine.get_fantasy_scores_for_team(delivery_id, team)

    return ai_service.explain_delivery(
        match_id=engine.metadata.match_id,
        delivery=delivery,
        snapshot=snapshot,
        fantasy_impact=ball_delta,
        ruleset_version=engine.ruleset.version
    )

