from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.scoring.ruleset import RulesetConfig, StrikeRateRule, EconomyRateRule

class ScoringRuleItem(BaseModel):
    category: str
    name: str
    description: str
    points: float

class BreakdownItem(BaseModel):
    category: str
    label: str
    count: int = 1
    points_each: float
    total_points: float

class PlayerFantasyScore(BaseModel):
    player_name: str
    team: str
    role: str
    is_captain: bool = False
    is_vice_captain: bool = False
    multiplier: float = 1.0
    raw_points: float = 0.0
    total_points: float = 0.0
    breakdown: List[BreakdownItem] = Field(default_factory=list)
    recent_delta: float = 0.0

class PlayerDelta(BaseModel):
    player_name: str
    team: str
    reason: str
    category: str
    raw_delta: float
    multiplier: float
    net_delta: float
    previous_total: float
    new_total: float
    is_captain: bool
    is_vice_captain: bool

class BallFantasyImpact(BaseModel):
    delivery_index: int
    over_display: str
    player_deltas: List[PlayerDelta] = Field(default_factory=list)
    fantasy_team_total: float = 0.0
    fantasy_team_delta: float = 0.0
    summary_sentence: str

class FantasyTeamConfig(BaseModel):
    selected_players: List[str]
    captain: str
    vice_captain: str

class FantasyScoreResponse(BaseModel):
    delivery_index: int
    over_display: str
    player_scores: Dict[str, PlayerFantasyScore]
    ball_delta: BallFantasyImpact
    team_total: float
    team_delta: float
