import pytest
from app.models.match import Delivery, MatchMetadata, PlayerInfo, WicketDetail
from app.models.fantasy import RulesetConfig, FantasyTeamConfig
from app.services.fantasy_engine import FantasyEngine
from app.replay.engine import ReplayEngine
from app.ai.service import AIExplanationService

@pytest.fixture
def test_metadata():
    return MatchMetadata(
        match_id="test_match_correctness",
        event_name="T20 Match Test",
        venue="Test Ground",
        city="Test City",
        dates=["2026-10-30"],
        teams=["Team A", "Team B"],
        toss={"winner": "Team A", "decision": "bat"},
        outcome={"winner": "Team A"},
        total_deliveries=10,
        players={
            "Team A": ["V Kohli", "RG Sharma", "RR Pant", "AR Patel"],
            "Team B": ["JJ Bumrah", "Q de Kock", "H Klaasen", "KA Maharaj"]
        },
        roster=[
            PlayerInfo(name="V Kohli", team="Team A", role="BAT", credits=9.5),
            PlayerInfo(name="RG Sharma", team="Team A", role="BAT", credits=9.0),
            PlayerInfo(name="RR Pant", team="Team A", role="WK", credits=8.5),
            PlayerInfo(name="AR Patel", team="Team A", role="AR", credits=8.0),
            PlayerInfo(name="JJ Bumrah", team="Team B", role="BOWL", credits=9.5),
            PlayerInfo(name="Q de Kock", team="Team B", role="WK", credits=9.0),
            PlayerInfo(name="H Klaasen", team="Team B", role="WK", credits=8.5),
            PlayerInfo(name="KA Maharaj", team="Team B", role="BOWL", credits=8.0),
        ]
    )

@pytest.fixture
def ruleset():
    return RulesetConfig()

# =====================================================================
# 1. NON-BOUNDARY FOURS AND SIXES
# =====================================================================

def test_overthrow_four_does_not_award_boundary_bonus(test_metadata, ruleset):
    """An overthrow four (runs.non_boundary: true) awards 4 run pts but 0 four bonus."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=4, extra_runs=0, total_runs=4,
            non_boundary=True,
            is_four=False,  # Engine sets is_four=False for non_boundary hits
            is_six=False,
            summary="4 runs via overthrows"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("V Kohli", 0)

    # Expected: Starting XI: 4.0 + 4 Runs Scored: 4.0 = 8.0 (NO +4 boundary four bonus)
    assert score.raw_points == 8.0
    labels = [item.label for item in score.breakdown]
    assert any("Runs Scored" in l for l in labels)
    assert not any("Boundary 4" in l for l in labels)

def test_running_all_run_four_does_not_award_boundary_bonus(test_metadata, ruleset):
    """An all-run four (runs.non_boundary: true) awards 4 run pts but 0 four bonus."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=4, extra_runs=0, total_runs=4,
            non_boundary=True, is_four=False, is_six=False,
            summary="4 runs completed by running"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("V Kohli", 0)
    assert score.raw_points == 8.0
    labels = [item.label for item in score.breakdown]
    assert not any("Boundary 4" in l for l in labels)

def test_genuine_boundary_four_awards_boundary_bonus(test_metadata, ruleset):
    """A genuine boundary four (non_boundary: false) awards 4 run pts + 4 four bonus = 8 pts."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=4, extra_runs=0, total_runs=4,
            non_boundary=False, is_four=True, is_six=False,
            summary="FOUR to the fence"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("V Kohli", 0)

    # Starting XI: 4.0 + Runs (4): 4.0 + Boundary 4 bonus: 4.0 = 12.0
    assert score.raw_points == 12.0
    labels = [item.label for item in score.breakdown]
    assert any("Boundary 4" in l for l in labels)

def test_non_boundary_six_does_not_award_six_bonus(test_metadata, ruleset):
    """Non-boundary six (non_boundary: true) awards 6 run pts but 0 six bonus."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=6, extra_runs=0, total_runs=6,
            non_boundary=True, is_four=False, is_six=False,
            summary="6 runs (overthrows)"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("V Kohli", 0)
    # Starting XI: 4.0 + Runs (6): 6.0 = 10.0 (NO +6 six bonus)
    assert score.raw_points == 10.0
    labels = [item.label for item in score.breakdown]
    assert not any("Boundary 6" in l for l in labels)

# =====================================================================
# 2. DIRECT-HIT RUN-OUTS
# =====================================================================

def test_run_out_without_direct_hit_evidence_withholds_direct_hit_bonus(test_metadata, ruleset):
    """Single fielder involved without explicit direct-hit evidence receives shared/standard run out points (+6), NOT +12."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=2, ball_in_over=3, over_display="2.3",
            batter="AR Patel", bowler="JJ Bumrah", non_striker="V Kohli",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True, wicket_kind="run out", player_out="AR Patel",
            fielders=["Q de Kock"],
            direct_hit=None,  # Source evidence unavailable
            wickets=[WicketDetail(kind="run out", player_out="AR Patel", fielders=["Q de Kock"])],
            summary="Run out"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score_qdk = engine.calculate_player_points_at("Q de Kock", 0)

    # Starting XI: 4.0 + Run Out (Standard): 6.0 = 10.0 (NOT +12.0)
    assert score_qdk.raw_points == 10.0
    labels = [item.label for item in score_qdk.breakdown]
    assert any("Run Outs" in l for l in labels)
    assert not any("Direct Run Outs" in l for l in labels)

def test_run_out_with_verified_direct_hit_evidence_awards_full_bonus(test_metadata, ruleset):
    """Fielder with verified direct_hit=True receives +12 pts direct hit run out."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=2, ball_in_over=3, over_display="2.3",
            batter="AR Patel", bowler="JJ Bumrah", non_striker="V Kohli",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True, wicket_kind="run out", player_out="AR Patel",
            fielders=["Q de Kock"],
            direct_hit=True,  # Verified direct-hit in source data
            wickets=[WicketDetail(kind="run out", player_out="AR Patel", fielders=["Q de Kock"])],
            summary="Direct hit run out"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score_qdk = engine.calculate_player_points_at("Q de Kock", 0)

    # Starting XI: 4.0 + Direct Run Out: 12.0 = 16.0
    assert score_qdk.raw_points == 16.0
    labels = [item.label for item in score_qdk.breakdown]
    assert any("Direct Run Outs" in l for l in labels)

def test_run_out_explanation_discloses_missing_direct_hit_evidence():
    """Explanation explicitly notes that Cricsheet records participants but lacks direct-hit telemetry."""
    dlv = Delivery(
        index=84, innings=1, team_batting="Team A", team_bowling="Team B",
        over=13, ball_in_over=4, over_display="13.4",
        batter="AR Patel", bowler="KA Maharaj", non_striker="V Kohli",
        batter_runs=0, extra_runs=0, total_runs=0,
        is_wicket=True, wicket_kind="run out", player_out="AR Patel",
        fielders=["Q de Kock"], direct_hit=None,
        summary="RUN OUT! AR Patel dismissed by Q de Kock."
    )
    from app.models.match import SnapshotState, BatterLiveStats, BowlerLiveStats
    from app.models.fantasy import BallFantasyImpact
    snapshot = SnapshotState(
        delivery_index=84, over_display="13.4", innings=1,
        batting_team="Team A", bowling_team="Team B",
        team_score=106, team_wickets=4, overs_display="13.4",
        legal_balls_bowled=82, run_rate=7.75,
        striker=BatterLiveStats(name="AR Patel", runs=47, balls=31, fours=1, sixes=4),
        bowler=BowlerLiveStats(name="KA Maharaj", overs=3.0, legal_balls=18, runs_conceded=23, wickets=2),
        match_status="1st Innings: Team A batting",
        delivery_event=dlv
    )
    impact = BallFantasyImpact(
        delivery_index=84, over_display="13.4",
        player_deltas=[], fantasy_team_total=0.0, fantasy_team_delta=0.0,
        summary_sentence="Run out"
    )

    ai_svc = AIExplanationService()
    explanation = ai_svc._generate_deterministic_explanation(dlv, snapshot, impact)

    # Must disclose missing direct-hit evidence in unavailable_evidence
    unavail_text = " ".join(explanation.evidence.unavailable_evidence)
    assert "direct hit" in unavail_text.lower() or "direct-hit" in unavail_text.lower()
    assert "withheld" in unavail_text.lower() or "standard" in unavail_text.lower()

# =====================================================================
# 3. MAIDEN OVERS
# =====================================================================

def test_maiden_over_awarded_only_for_completed_six_ball_over(test_metadata, ruleset):
    """A completed 6-ball over with 0 bowler runs is awarded a maiden over (+12 pts)."""
    deliveries = [
        Delivery(
            index=i, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=i + 1, over_display=f"0.{i+1}",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_dot=True,
            is_maiden_completing_ball=(i == 5),  # 6th ball of completed maiden
            summary="Dot ball"
        ) for i in range(6)
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("JJ Bumrah", 5)

    # Starting XI: 4.0 + 6 Dot Balls: 6.0 + Maiden Over: 12.0 = 22.0
    assert score.raw_points == 22.0
    labels = [item.label for item in score.breakdown]
    assert any("Maiden Overs" in l for l in labels)

def test_maiden_over_with_byes_and_legbyes_qualifies(test_metadata, ruleset):
    """Runs from byes or legbyes are uncharged to bowler; completed over with 0 bowler runs IS a maiden."""
    # 5 dot balls + 1 ball with 4 byes (extras_runs=4, extra_type='byes')
    deliveries = [
        Delivery(
            index=i, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=i + 1, over_display=f"0.{i+1}",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=0,
            extra_runs=4 if i == 2 else 0,
            total_runs=4 if i == 2 else 0,
            extra_type="byes" if i == 2 else None,
            is_dot=(i != 2),
            is_maiden_completing_ball=(i == 5),
            summary="Byes" if i == 2 else "Dot ball"
        ) for i in range(6)
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("JJ Bumrah", 5)

    # Starting XI: 4.0 + 6 Dot Balls (0 runs conceded by bowler): 6.0 + Maiden: 12.0 = 22.0
    assert score.raw_points == 22.0
    labels = [item.label for item in score.breakdown]
    assert any("Maiden Overs" in l for l in labels)

def test_incomplete_over_does_not_award_maiden(test_metadata, ruleset):
    """An incomplete over (e.g. 4 legal balls before innings ends) cannot be awarded a maiden."""
    deliveries = [
        Delivery(
            index=i, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=i + 1, over_display=f"0.{i+1}",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_dot=True,
            is_maiden_completing_ball=False,  # Incomplete over: false
            summary="Dot ball"
        ) for i in range(4)
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("JJ Bumrah", 3)

    # Starting XI: 4.0 + 4 Dot Balls: 4.0 = 8.0 (NO maiden over bonus)
    assert score.raw_points == 8.0
    labels = [item.label for item in score.breakdown]
    assert not any("Maiden Overs" in l for l in labels)

# =====================================================================
# 4. MULTIPLE WICKET EVENTS
# =====================================================================

def test_multiple_wickets_on_single_delivery_processed_completely(test_metadata, ruleset):
    """Deliveries containing multiple wickets in Cricsheet data do not silently drop subsequent wickets."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=19, ball_in_over=6, over_display="19.6",
            batter="RR Pant", bowler="JJ Bumrah", non_striker="AR Patel",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True,
            wicket_kind="bowled",
            player_out="RR Pant",
            fielders=["Q de Kock"],
            direct_hit=None,
            wickets=[
                WicketDetail(kind="bowled", player_out="RR Pant", fielders=[]),
                WicketDetail(kind="run out", player_out="AR Patel", fielders=["Q de Kock"])
            ],
            summary="Double wicket"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)

    # 1. Batter 1 out: RR Pant
    score_pant = engine.calculate_player_points_at("RR Pant", 0)
    assert any("Dismissal for Duck" in item.label for item in score_pant.breakdown)

    # 2. Batter 2 out: AR Patel (subsequent wicket entry not ignored)
    score_axar = engine.calculate_player_points_at("AR Patel", 0)
    assert any("Dismissal for Duck" in item.label for item in score_axar.breakdown)

    # 3. Bowler credit: Bumrah gets credit for RR Pant bowled (30w + 8 bonus + 1 dot = 39 pts)
    score_bumrah = engine.calculate_player_points_at("JJ Bumrah", 0)
    b_labels = [item.label for item in score_bumrah.breakdown]
    assert any("Wickets Taken" in l for l in b_labels)
    assert any("Bowled / LBW Bonus" in l for l in b_labels)

    # 4. Fielder credit: Q de Kock gets credit for AR Patel run out
    score_qdk = engine.calculate_player_points_at("Q de Kock", 0)
    q_labels = [item.label for item in score_qdk.breakdown]
    assert any("Run Outs" in l for l in q_labels)

def test_boundary_four_off_noball_qualifies_for_bonus(test_metadata, ruleset):
    """A boundary four hit off a no-ball qualifies for the boundary four bonus."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=4, extra_runs=1, total_runs=5,
            extra_type="noballs",
            non_boundary=False, is_four=True, is_six=False,
            summary="FOUR off a no-ball!"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("V Kohli", 0)

    # Starting XI: 4.0 + Runs (4): 4.0 + Boundary 4 bonus: 4.0 = 12.0
    assert score.raw_points == 12.0
    labels = [item.label for item in score.breakdown]
    assert any("Boundary 4" in l for l in labels)

def test_multi_fielder_run_out_awards_shared_points_to_both_fielders(test_metadata, ruleset):
    """When multiple fielders participate in a run-out, both receive shared run-out points (+6)."""
    deliveries = [
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=2, ball_in_over=3, over_display="2.3",
            batter="AR Patel", bowler="JJ Bumrah", non_striker="V Kohli",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_wicket=True, wicket_kind="run out", player_out="AR Patel",
            fielders=["Q de Kock", "KA Maharaj"],
            direct_hit=None,
            wickets=[WicketDetail(kind="run out", player_out="AR Patel", fielders=["Q de Kock", "KA Maharaj"])],
            summary="Relay run out by Q de Kock and KA Maharaj"
        )
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score_qdk = engine.calculate_player_points_at("Q de Kock", 0)
    score_km = engine.calculate_player_points_at("KA Maharaj", 0)

    # Both get Starting XI (4.0) + Run Out Shared (6.0) = 10.0
    assert score_qdk.raw_points == 10.0
    assert score_km.raw_points == 10.0
    assert any("Run Outs" in item.label for item in score_qdk.breakdown)
    assert any("Run Outs" in item.label for item in score_km.breakdown)

def test_maiden_over_disqualified_by_wide_extra(test_metadata, ruleset):
    """An over with 1 wide (+1 extra conceded by bowler) is NOT a maiden over."""
    deliveries = [
        # Ball 1: wide
        Delivery(
            index=0, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=1, over_display="0.1",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=0, extra_runs=1, total_runs=1, extra_type="wides",
            is_dot=False, is_maiden_completing_ball=False, summary="Wide"
        )
    ] + [
        # Balls 2-7: 6 legal dots
        Delivery(
            index=i+1, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=i + 2, over_display=f"0.{i+2}",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_dot=True, is_maiden_completing_ball=False, summary="Dot ball"
        ) for i in range(6)
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score = engine.calculate_player_points_at("JJ Bumrah", 6)

    # Starting XI: 4.0 + 6 Dot Balls: 6.0 = 10.0 (NO maiden over bonus)
    assert score.raw_points == 10.0
    labels = [item.label for item in score.breakdown]
    assert not any("Maiden Overs" in l for l in labels)

def test_maiden_over_disqualified_if_bowled_by_multiple_bowlers(test_metadata, ruleset):
    """An over shared between two bowlers (e.g. injury) does not award a maiden to either."""
    deliveries = [
        # Bowler 1 bowls 3 dots
        Delivery(
            index=i, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=i + 1, over_display=f"0.{i+1}",
            batter="V Kohli", bowler="JJ Bumrah", non_striker="RG Sharma",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_dot=True, is_maiden_completing_ball=False, summary="Dot ball"
        ) for i in range(3)
    ] + [
        # Bowler 2 bowls 3 dots
        Delivery(
            index=i+3, innings=1, team_batting="Team A", team_bowling="Team B",
            over=0, ball_in_over=i + 4, over_display=f"0.{i+4}",
            batter="V Kohli", bowler="KA Maharaj", non_striker="RG Sharma",
            batter_runs=0, extra_runs=0, total_runs=0,
            is_dot=True, is_maiden_completing_ball=False, summary="Dot ball"
        ) for i in range(3)
    ]
    engine = FantasyEngine(deliveries, test_metadata, ruleset)
    score_bumrah = engine.calculate_player_points_at("JJ Bumrah", 5)
    score_maharaj = engine.calculate_player_points_at("KA Maharaj", 5)

    assert not any("Maiden Overs" in l.label for l in score_bumrah.breakdown)
    assert not any("Maiden Overs" in l.label for l in score_maharaj.breakdown)

def test_ai_explanation_for_multiple_wickets_on_single_delivery():
    """AI service explains multiple dismissals occurring on the same delivery."""
    dlv = Delivery(
        index=120, innings=1, team_batting="Team A", team_bowling="Team B",
        over=19, ball_in_over=6, over_display="19.6",
        batter="RR Pant", bowler="JJ Bumrah", non_striker="AR Patel",
        batter_runs=0, extra_runs=0, total_runs=0,
        is_wicket=True, wicket_kind="bowled", player_out="RR Pant, AR Patel",
        fielders=["Q de Kock"],
        wickets=[
            WicketDetail(kind="bowled", player_out="RR Pant", fielders=[]),
            WicketDetail(kind="run out", player_out="AR Patel", fielders=["Q de Kock"])
        ],
        summary="MULTIPLE WICKETS! RR Pant (bowled), AR Patel (run out) off JJ Bumrah!"
    )
    from app.models.match import SnapshotState, BatterLiveStats, BowlerLiveStats
    from app.models.fantasy import BallFantasyImpact
    snapshot = SnapshotState(
        delivery_index=120, over_display="19.6", innings=1,
        batting_team="Team A", bowling_team="Team B",
        team_score=170, team_wickets=7, overs_display="19.6",
        legal_balls_bowled=120, run_rate=8.5,
        striker=BatterLiveStats(name="RR Pant", runs=0, balls=1),
        bowler=BowlerLiveStats(name="JJ Bumrah", overs=4.0, legal_balls=24, runs_conceded=18, wickets=3),
        match_status="1st Innings: Team A completed",
        delivery_event=dlv
    )
    impact = BallFantasyImpact(
        delivery_index=120, over_display="19.6",
        player_deltas=[], fantasy_team_total=0.0, fantasy_team_delta=0.0,
        summary_sentence="Double dismissal"
    )

    ai_svc = AIExplanationService()
    exp = ai_svc._generate_deterministic_explanation(dlv, snapshot, impact)

    assert "DOUBLE WICKET" in exp.headline
    assert "RR Pant" in exp.what_happened and "AR Patel" in exp.what_happened
    grounded_text = " ".join(exp.evidence.grounded_in_data)
    assert "RR Pant (bowled)" in grounded_text
    assert "AR Patel (run out)" in grounded_text
