from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class StrikeRateRule(BaseModel):
    min_balls: int = 10
    tier_above_170: float = 6.0
    tier_150_to_170: float = 4.0
    tier_130_to_150: float = 2.0
    tier_60_to_70: float = -2.0
    tier_50_to_60: float = -4.0
    tier_below_50: float = -6.0

class EconomyRateRule(BaseModel):
    min_legal_balls: int = 12  # 2 completed overs
    tier_below_5: float = 6.0
    tier_5_to_6: float = 4.0
    tier_6_to_7: float = 2.0
    tier_10_to_11: float = -2.0
    tier_11_to_12: float = -4.0
    tier_above_12: float = -6.0

class RulesetConfig(BaseModel):
    ruleset_id: str = "dream11_standard_t20_v2025"
    ruleset_name: str = "Dream11 Standard T20 Scoring System"
    version: str = "2025.1.0"
    format: str = "T20 (Standard)"
    source_url: str = "https://www.dream11.com/fantasy-cricket/point-system"
    last_verified: str = "2025-01-01"
    retrospective_disclosure: str = (
        "Standard Dream11 T20 scoring rules applied retrospectively to the ICC Men's "
        "T20 World Cup 2024 Final for analytics and demonstration purposes."
    )

    # General / Lineup
    starting_xi: float = 4.0
    captain_multiplier: float = 2.0
    vice_captain_multiplier: float = 1.5

    # Batting
    run: float = 1.0
    boundary_four_bonus: float = 4.0      # Official Dream11 Standard T20: +4 bonus (total 8 pts with 4 runs)
    six_bonus: float = 6.0                # Official Dream11 Standard T20: +6 bonus (total 12 pts with 6 runs)
    twenty_five_run_bonus: float = 4.0    # 25-run bonus
    half_century_bonus: float = 8.0       # Replaces 25-run bonus (non-stacking: +8 total)
    seventy_five_run_bonus: float = 12.0  # Replaces half-century bonus (non-stacking: +12 total)
    century_bonus: float = 16.0           # Replaces 75-run bonus (non-stacking: +16 total)
    duck_penalty: float = -2.0            # Dismissal on 0 runs (BAT, WK, AR only; not BOWL)
    strike_rate: StrikeRateRule = Field(default_factory=StrikeRateRule)

    # Bowling
    wicket_normal: float = 30.0           # Official Dream11 Standard T20: +30 pts per wicket (excl. run out)
    lbw_bowled_bonus: float = 8.0         # Official Dream11: +8 bonus (+38 pts total for LBW/Bowled)
    dot_ball_bowled: float = 1.0          # Official Dream11 Standard T20: +1 pt per dot ball bowled
    three_wicket_bonus: float = 4.0       # 3-wicket haul bonus
    four_wicket_bonus: float = 8.0        # Replaces 3-wicket bonus (non-stacking: +8 total)
    five_wicket_bonus: float = 12.0       # Replaces 4-wicket bonus (non-stacking: +12 total)
    maiden_over: float = 12.0             # 0 runs conceded by bowler in completed 6-ball over
    economy_rate: EconomyRateRule = Field(default_factory=EconomyRateRule)

    # Fielding
    catch: float = 8.0
    three_catch_bonus: float = 4.0
    stumping: float = 12.0
    run_out_direct: float = 12.0
    run_out_shared: float = 6.0

DEFAULT_RULESET = RulesetConfig()
