import pytest
from app.models.fantasy import RulesetConfig, FantasyTeamConfig
from app.models.match import Delivery, MatchMetadata, PlayerInfo
from app.services.fantasy_engine import FantasyEngine

@pytest.fixture
def sample_metadata():
    return MatchMetadata(
        match_id="test_match_1",
        event_name="ICC Men's T20 World Cup",
        venue="Kensington Oval",
        city="Bridgetown",
        dates=["2024-06-29"],
        teams=["South Africa", "India"],
        toss={"winner": "India", "decision": "bat"},
        outcome={"winner": "India"},
        total_deliveries=5,
        players={
            "India": ["V Kohli", "HH Pandya", "JJ Bumrah", "RG Sharma"],
            "South Africa": ["Q de Kock", "H Klaasen", "K Rabada", "DA Miller"]
        },
        roster=[
            PlayerInfo(name="V Kohli", team="India", role="BAT", credits=9.5),
            PlayerInfo(name="HH Pandya", team="India", role="AR", credits=9.0),
            PlayerInfo(name="JJ Bumrah", team="India", role="BOWL", credits=9.5),
            PlayerInfo(name="RG Sharma", team="India", role="BAT", credits=9.0),
            PlayerInfo(name="Q de Kock", team="South Africa", role="WK", credits=9.0),
            PlayerInfo(name="H Klaasen", team="South Africa", role="WK", credits=9.0),
            PlayerInfo(name="K Rabada", team="South Africa", role="BOWL", credits=8.5),
            PlayerInfo(name="DA Miller", team="South Africa", role="BAT", credits=8.5),
        ]
    )

@pytest.fixture
def ruleset():
    return RulesetConfig()

def test_starting_xi_bonus(sample_metadata, ruleset):
    """Every player in starting XI receives +4 points base."""
    deliveries = []
    engine = FantasyEngine(deliveries, sample_metadata, ruleset)
    score = engine.calculate_player_points_at("V Kohli", 0, is_captain=False, is_vice_captain=False)
    assert score.raw_points == 4.0
    assert score.total_points == 4.0

def test_captain_and_vice_captain_multipliers(sample_metadata, ruleset):
    """Captain gets 2x, Vice-Captain gets 1.5x points."""
    deliveries = []
    engine = FantasyEngine(deliveries, sample_metadata, ruleset)
    
    score_regular = engine.calculate_player_points_at("V Kohli", 0, is_captain=False, is_vice_captain=False)
    score_c = engine.calculate_player_points_at("V Kohli", 0, is_captain=True, is_vice_captain=False)
    score_vc = engine.calculate_player_points_at("V Kohli", 0, is_captain=False, is_vice_captain=True)

    assert score_regular.total_points == 4.0
    assert score_c.total_points == 8.0     # 4.0 * 2.0
    assert score_vc.total_points == 6.0    # 4.0 * 1.5

def test_batting_boundary_and_six_bonus(sample_metadata, ruleset):
    """Standard T20: Four gives +4 bonus (+8 total). Six gives +6 bonus (+12 total)."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="India", team_bowling="South Africa",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="K Rabada", non_striker="RG Sharma",
            batter_runs=4, extra_runs=0, total_runs=4,
            is_four=True, is_six=False, is_dot=False, is_wicket=False,
            summary="FOUR!"
        ),
        Delivery(
            index=1, innings=1, team_batting="India", team_bowling="South Africa",
            over=0, ball_in_over=2, over_display="0.2",
            batter="V Kohli", bowler="K Rabada", non_striker="RG Sharma",
            batter_runs=6, extra_runs=0, total_runs=6,
            is_four=False, is_six=True, is_dot=False, is_wicket=False,
            summary="SIX!"
        )
    ]
    engine = FantasyEngine(deliveries, sample_metadata, ruleset)
    score = engine.calculate_player_points_at("V Kohli", 1, is_captain=False, is_vice_captain=False)
    # Expected:
    # Starting XI: 4
    # Runs (10): 10
    # Boundary 4 bonus (1): 4
    # Boundary 6 bonus (1): 6
    # Total raw = 4 + 10 + 4 + 6 = 24.0
    assert score.raw_points == 24.0
    assert score.total_points == 24.0

def test_dot_ball_bowled(sample_metadata, ruleset):
    """Every dot ball bowled awards +1 pt to the bowler in Standard T20."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="South Africa", team_bowling="India",
            over=0, ball_in_over=1, over_display="0.1",
            batter="Q de Kock", bowler="JJ Bumrah", non_striker="DA Miller",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_dot=True, summary="Dot ball"
        ),
        Delivery(
            index=1, innings=1, team_batting="South Africa", team_bowling="India",
            over=0, ball_in_over=2, over_display="0.2",
            batter="Q de Kock", bowler="JJ Bumrah", non_striker="DA Miller",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_dot=True, summary="Dot ball"
        )
    ]
    engine = FantasyEngine(deliveries, sample_metadata, ruleset)
    score = engine.calculate_player_points_at("JJ Bumrah", 1)
    # Starting XI: 4 + 2 Dot balls: 2 = 6.0
    assert score.total_points == 6.0

def test_wicket_and_lbw_bowled_bonus(sample_metadata, ruleset):
    """Standard T20: Wicket gives +30 pts. LBW or Bowled adds +8 pts bonus (+38 total)."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="South Africa", team_bowling="India",
            over=1, ball_in_over=1, over_display="1.1",
            batter="Q de Kock", bowler="JJ Bumrah", non_striker="DA Miller",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True, wicket_kind="bowled", player_out="Q de Kock",
            summary="Wicket Bowled"
        )
    ]
    engine = FantasyEngine(deliveries, sample_metadata, ruleset)
    score_bowler = engine.calculate_player_points_at("JJ Bumrah", 0)
    # Expected for Bumrah:
    # Starting XI: 4
    # Wicket: 30
    # Bowled Bonus: 8
    # Dot ball bowled: 1 (0 runs conceded on legal delivery)
    # Total = 4 + 30 + 8 + 1 = 43.0
    assert score_bowler.total_points == 43.0

def test_duck_penalty_for_top_order(sample_metadata, ruleset):
    """Batter dismissed for 0 receives -2 pts penalty."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="South Africa", team_bowling="India",
            over=1, ball_in_over=1, over_display="1.1",
            batter="Q de Kock", bowler="JJ Bumrah", non_striker="DA Miller",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True, wicket_kind="lbw", player_out="Q de Kock",
            summary="Wicket LBW"
        )
    ]
    engine = FantasyEngine(deliveries, sample_metadata, ruleset)
    score_batter = engine.calculate_player_points_at("Q de Kock", 0)
    # Starting XI: 4 + Duck penalty: -2 = 2.0
    assert score_batter.total_points == 2.0

def test_fielding_catch_points(sample_metadata, ruleset):
    """Catch awards +8 pts to the fielder."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="South Africa", team_bowling="India",
            over=3, ball_in_over=6, over_display="3.6",
            batter="DA Miller", bowler="HH Pandya", non_striker="Q de Kock",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True, wicket_kind="caught", player_out="DA Miller",
            fielders=["V Kohli"],
            summary="Caught V Kohli b HH Pandya"
        )
    ]
    engine = FantasyEngine(deliveries, sample_metadata, ruleset)
    score_fielder = engine.calculate_player_points_at("V Kohli", 0)
    # Starting XI: 4 + Catch: 8 = 12.0
    assert score_fielder.total_points == 12.0

def test_milestone_bonuses_batting(sample_metadata, ruleset):
    """Test 25-run (+4), 50-run (+8 replacing 25), 75-run (+12 replacing 50), 100-run (+16 replacing 75)."""
    # 26 runs: 4 starting + 26 runs + 4 (25-run bonus) = 34.0
    d_25 = [
        Delivery(
            index=0, innings=1, team_batting="India", team_bowling="South Africa",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="K Rabada", non_striker="RG Sharma",
            batter_runs=26, extra_runs=0, total_runs=26, summary="26 runs"
        )
    ]
    e_25 = FantasyEngine(d_25, sample_metadata, ruleset)
    s_25 = e_25.calculate_player_points_at("V Kohli", 0)
    assert s_25.total_points == 4.0 + 26.0 + 4.0

    # 52 runs: 4 starting + 52 runs + 8 (Half-century, replaces 25) = 64.0
    d_50 = [
        Delivery(
            index=0, innings=1, team_batting="India", team_bowling="South Africa",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="K Rabada", non_striker="RG Sharma",
            batter_runs=52, extra_runs=0, total_runs=52, summary="52 runs"
        )
    ]
    e_50 = FantasyEngine(d_50, sample_metadata, ruleset)
    s_50 = e_50.calculate_player_points_at("V Kohli", 0)
    assert s_50.total_points == 4.0 + 52.0 + 8.0

    # 76 runs: 4 starting + 76 runs + 12 (75-run bonus, replaces 50) = 92.0
    d_75 = [
        Delivery(
            index=0, innings=1, team_batting="India", team_bowling="South Africa",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="K Rabada", non_striker="RG Sharma",
            batter_runs=76, extra_runs=0, total_runs=76, summary="76 runs"
        )
    ]
    e_75 = FantasyEngine(d_75, sample_metadata, ruleset)
    s_75 = e_75.calculate_player_points_at("V Kohli", 0)
    assert s_75.total_points == 4.0 + 76.0 + 12.0

def test_bowling_wicket_hauls(sample_metadata, ruleset):
    """3 wickets = +4 bonus. 4 wickets = +8 bonus (replacing 3). 5 wickets = +12 bonus (replacing 4)."""
    deliveries_3w = [
        Delivery(
            index=i, innings=1, team_batting="South Africa", team_bowling="India",
            over=i, ball_in_over=1, over_display=f"{i}.1",
            batter="Q de Kock", bowler="JJ Bumrah", non_striker="DA Miller",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True, wicket_kind="caught", player_out="Q de Kock",
            fielders=["V Kohli"], summary="Wicket"
        ) for i in range(3)
    ]
    engine_3w = FantasyEngine(deliveries_3w, sample_metadata, ruleset)
    score_3w = engine_3w.calculate_player_points_at("JJ Bumrah", 2)
    # Starting: 4 + Wickets: 3 * 30 = 90 + Dot balls: 3 * 1 = 3 + 3-Wicket Bonus: 4 => 101.0
    assert score_3w.total_points == 4.0 + 90.0 + 3.0 + 4.0

    # 5 wickets: haul bonus is +12 (not +16)
    deliveries_5w = [
        Delivery(
            index=i, innings=1, team_batting="South Africa", team_bowling="India",
            over=i, ball_in_over=1, over_display=f"{i}.1",
            batter="Q de Kock", bowler="JJ Bumrah", non_striker="DA Miller",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True, wicket_kind="caught", player_out="Q de Kock",
            fielders=["V Kohli"], summary="Wicket"
        ) for i in range(5)
    ]
    engine_5w = FantasyEngine(deliveries_5w, sample_metadata, ruleset)
    score_5w = engine_5w.calculate_player_points_at("JJ Bumrah", 4)
    # Starting: 4 + Wickets: 5 * 30 = 150 + Dot balls: 5 * 1 = 5 + 5-Wicket Bonus: 12 => 171.0
    assert score_5w.total_points == 4.0 + 150.0 + 5.0 + 12.0

def test_maiden_over_points(sample_metadata, ruleset):
    """Maiden over awards +12 pts to bowler."""
    deliveries_maiden = [
        Delivery(
            index=0, innings=1, team_batting="South Africa", team_bowling="India",
            over=0, ball_in_over=6, over_display="0.6",
            batter="Q de Kock", bowler="JJ Bumrah", non_striker="DA Miller",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_dot=True, is_maiden_completing_ball=True, summary="Maiden completed"
        )
    ]
    engine = FantasyEngine(deliveries_maiden, sample_metadata, ruleset)
    score = engine.calculate_player_points_at("JJ Bumrah", 0)
    # Starting: 4 + Dot ball: 1 + Maiden: 12 = 17.0
    assert score.total_points == 17.0
