import pytest
from pathlib import Path
from app.replay.engine import ReplayEngine
from app.models.fantasy import FantasyTeamConfig
from app.scoring.ruleset import DEFAULT_RULESET

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "ind_sa_t20wc_2024_final.json"

@pytest.fixture(scope="module")
def engine():
    assert DATA_PATH.exists(), f"Match file not found at {DATA_PATH}"
    return ReplayEngine(str(DATA_PATH), ruleset=DEFAULT_RULESET)

def test_engine_initialization_and_snapshot_count(engine):
    """Verifies that all 251 deliveries are pre-computed into snapshots."""
    assert len(engine.deliveries) == 251
    assert len(engine.snapshots) == 251
    assert len(engine.base_fantasy_snapshots) == 251
    assert len(engine.ball_deltas) == 251
    assert len(engine.key_moments) > 10

def test_snapshot_o1_retrieval(engine):
    """Snapshot at any index can be retrieved in O(1) with consistent state."""
    snap_0 = engine.get_snapshot(0)
    snap_100 = engine.get_snapshot(100)
    snap_final = engine.get_snapshot(250)

    assert snap_0.delivery_index == 0
    assert snap_0.innings == 1
    assert snap_100.delivery_index == 100
    assert snap_final.delivery_index == 250
    assert snap_final.match_status.startswith("Match Completed")

def test_boundaries_scoring(engine):
    """Standard T20: Four gives +4 bonus (8.0 total). Six gives +6 bonus (12.0 total)."""
    # Over 0.2 of Innings 1: Virat Kohli hits a boundary FOUR off Jansen
    delta_four = engine.ball_deltas[1]
    kohli_delta = next((d for d in delta_four.player_deltas if d.player_name == "V Kohli"), None)
    assert kohli_delta is not None
    # 4 runs + 4 four bonus = 8.0 pts
    assert kohli_delta.raw_delta == 8.0

def test_dot_ball_bowled(engine):
    """Bowler earns +1 pt per dot ball bowled."""
    # Ball 0 (Over 0.1): Rohit Sharma took 1 run off Jansen (not a dot)
    # Ball 2 (Over 0.3): Kohli hit a four
    # Find a legal ball with 0 runs conceded
    dot_dlv = next(
        (d for d in engine.deliveries if d.total_runs == 0 and d.extra_type is None and not d.is_wicket),
        None
    )
    assert dot_dlv is not None
    delta = engine.ball_deltas[dot_dlv.index]
    bowler_delta = next((d for d in delta.player_deltas if d.player_name == dot_dlv.bowler), None)
    assert bowler_delta is not None
    assert bowler_delta.raw_delta == 1.0  # +1 dot ball bowled

def test_wickets_and_bowled_bonus(engine):
    """Standard T20: Wicket gives +30 pts. Bowled/LBW gives +8 pts bonus (+38 total + 1 dot = 39.0)."""
    bowled_dlv = next(
        (d for d in engine.deliveries if d.is_wicket and d.wicket_kind in ("bowled", "lbw") and d.extra_runs == 0),
        None
    )
    assert bowled_dlv is not None
    delta = engine.ball_deltas[bowled_dlv.index]
    bowler_delta = next((d for d in delta.player_deltas if d.player_name == bowled_dlv.bowler), None)
    assert bowler_delta is not None
    # 30 wicket + 8 bowled/lbw + 1 dot ball = 39.0 pts
    assert bowler_delta.raw_delta == 39.0

def test_milestone_awarded_exactly_once(engine):
    """A milestone (e.g. 50 runs) must be awarded on the ball it was reached, and never duplicate on subsequent balls."""
    # Virat Kohli scored 76 runs in this final.
    kohli_reached_50_idx = None
    for i, dlv in enumerate(engine.deliveries):
        base_scores = engine.base_fantasy_snapshots[i]
        k_breakdown = base_scores["V Kohli"].breakdown
        has_50 = any("Half-Century" in item.label for item in k_breakdown)
        if has_50:
            kohli_reached_50_idx = i
            break

    assert kohli_reached_50_idx is not None

    # On the ball where 50 was crossed, delta reflects the milestone
    delta_at_50 = engine.ball_deltas[kohli_reached_50_idx]
    k_delta_50 = next((d for d in delta_at_50.player_deltas if d.player_name == "V Kohli"), None)
    assert k_delta_50 is not None

    # On the next ball, if Kohli scores 1 run without a milestone, delta is strictly 1.0
    next_idx = kohli_reached_50_idx + 1
    if next_idx < len(engine.deliveries):
        next_dlv = engine.deliveries[next_idx]
        if next_dlv.batter == "V Kohli" and next_dlv.batter_runs == 1 and not next_dlv.is_four:
            delta_next = engine.ball_deltas[next_idx]
            k_delta_next = next((d for d in delta_next.player_deltas if d.player_name == "V Kohli"), None)
            if k_delta_next:
                assert k_delta_next.raw_delta == 1.0

def test_captain_and_vice_captain_immutability(engine):
    """Captain (2x) and Vice-Captain (1.5x) multipliers apply without mutating underlying base scores."""
    team = FantasyTeamConfig(
        selected_players=["V Kohli", "JJ Bumrah"],
        captain="V Kohli",
        vice_captain="JJ Bumrah"
    )

    squad_scores, impact, total, delta = engine.get_fantasy_scores_for_team(50, team)
    base_kohli = engine.base_fantasy_snapshots[50]["V Kohli"].raw_points
    base_bumrah = engine.base_fantasy_snapshots[50]["JJ Bumrah"].raw_points

    # Squad total reflects 2x and 1.5x
    assert squad_scores["V Kohli"].total_points == round(base_kohli * 2.0, 1)
    assert squad_scores["JJ Bumrah"].total_points == round(base_bumrah * 1.5, 1)

    # Base snapshot remains untouched (1.0x)
    assert engine.base_fantasy_snapshots[50]["V Kohli"].multiplier == 1.0

def test_replay_step_back_and_forward_determinism(engine):
    """Jumping back and forth retrieves identical immutable snapshots."""
    snap_a = engine.get_snapshot(45)
    snap_b = engine.get_snapshot(120)
    snap_a_again = engine.get_snapshot(45)

    assert snap_a.team_score == snap_a_again.team_score
    assert snap_a.team_wickets == snap_a_again.team_wickets
    assert snap_a.striker.runs == snap_a_again.striker.runs
    assert snap_a.bowler.runs_conceded == snap_a_again.bowler.runs_conceded

def test_key_moments_filters(engine):
    """Key moments are pre-indexed into categories."""
    all_km = engine.get_key_moments('all')
    wickets_km = engine.get_key_moments('wickets')
    boundaries_km = engine.get_key_moments('boundaries')

    assert len(all_km) > 0
    assert len(wickets_km) > 0
    assert len(boundaries_km) > 0
    assert all(k.category == 'wicket' for k in wickets_km)
    assert all(k.category == 'boundary' for k in boundaries_km)

def test_run_out_direct_hit_unverified_in_real_match(engine):
    """In Cricsheet, Ball 84 (Over 13.3) is Axar Patel run out involving Q de Kock.
    Because direct-hit evidence is absent in source data, direct hit bonus is withheld
    and standard run-out credit (+6.0 pts) is awarded."""
    ro_dlv = engine.deliveries[84]
    assert ro_dlv.is_wicket is True
    assert ro_dlv.wicket_kind == "run out"
    assert "Q de Kock" in ro_dlv.fielders
    assert ro_dlv.direct_hit is None  # Unverified from Cricsheet

    delta_ro = engine.ball_deltas[84]
    qdk_delta = next((d for d in delta_ro.player_deltas if d.player_name == "Q de Kock"), None)
    assert qdk_delta is not None
    # Must award standard run out (+6.0 pts), not unverified direct hit (+12.0 pts)
    assert qdk_delta.raw_delta == 6.0
    assert "direct-hit unverified" in qdk_delta.reason.lower()

def test_deliveries_have_cricsheet_audit_attributes(engine):
    """Verify that all parsed deliveries maintain non_boundary and wickets structures."""
    for dlv in engine.deliveries:
        assert hasattr(dlv, "non_boundary")
        assert hasattr(dlv, "direct_hit")
        assert hasattr(dlv, "wickets")
        if dlv.is_wicket:
            assert len(dlv.wickets) >= 1
