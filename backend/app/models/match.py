from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class Fielder(BaseModel):
    name: str

class WicketDetail(BaseModel):
    kind: str
    player_out: str
    fielders: List[str] = Field(default_factory=list)

class Delivery(BaseModel):
    index: int
    innings: int
    team_batting: str
    team_bowling: str
    over: int
    ball_in_over: int
    over_display: str
    batter: str
    bowler: str
    non_striker: str
    batter_runs: int
    extra_runs: int
    total_runs: int
    extra_type: Optional[str] = None
    non_boundary: bool = False
    is_wicket: bool = False
    wicket_kind: Optional[str] = None
    player_out: Optional[str] = None
    fielders: List[str] = Field(default_factory=list)
    direct_hit: Optional[bool] = None
    wickets: List[WicketDetail] = Field(default_factory=list)
    is_four: bool = False
    is_six: bool = False
    is_dot: bool = False
    is_maiden_completing_ball: bool = False
    summary: str

class BatterLiveStats(BaseModel):
    name: str
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    strike_rate: float = 0.0
    is_out: bool = False
    dismissal_desc: Optional[str] = None

class BowlerLiveStats(BaseModel):
    name: str
    overs: float = 0.0
    legal_balls: int = 0
    maidens: int = 0
    runs_conceded: int = 0
    wickets: int = 0
    economy: float = 0.0

class KeyMoment(BaseModel):
    delivery_index: int
    over_display: str
    category: str  # wicket, boundary, milestone, climax
    title: str
    subtitle: str
    points_headline: Optional[str] = None

class RecentBallSummary(BaseModel):
    index: int
    over_display: str
    total_runs: number = 0 if False else int
    is_wicket: bool = False
    is_four: bool = False
    is_six: bool = False
    extra_type: Optional[str] = None

class SnapshotState(BaseModel):
    delivery_index: int
    over_display: str
    innings: int
    batting_team: str
    bowling_team: str
    team_score: int
    team_wickets: int
    overs_display: str
    legal_balls_bowled: int
    run_rate: float
    target: Optional[int] = None
    required_run_rate: Optional[float] = None
    runs_needed: Optional[int] = None
    balls_remaining: Optional[int] = None
    first_innings_team: Optional[str] = None
    first_innings_score: Optional[int] = None
    first_innings_wickets: Optional[int] = None
    first_innings_overs: Optional[str] = None
    first_innings_summary: Optional[str] = None
    striker: BatterLiveStats
    non_striker: Optional[BatterLiveStats] = None
    bowler: BowlerLiveStats
    recent_balls: List[Dict[str, Any]] = Field(default_factory=list)
    match_status: str
    is_key_moment: bool = False
    key_moment_info: Optional[KeyMoment] = None
    delivery_event: Delivery

class PlayerInfo(BaseModel):
    name: str
    team: str
    role: str  # WK, BAT, AR, BOWL
    credits: float = 8.5

class MatchMetadata(BaseModel):
    match_id: str
    event_name: str
    venue: str
    city: Optional[str] = None
    dates: List[str]
    teams: List[str]
    toss: Dict[str, Any]
    outcome: Dict[str, Any]
    total_deliveries: int
    players: Dict[str, List[str]]
    roster: List[PlayerInfo]
    source_attribution: str = "Data provided by Cricsheet (https://cricsheet.org), licensed under Open Data Commons Attribution License (ODC-BY 1.0)."

# Backwards compatibility alias
ScoreboardState = SnapshotState
