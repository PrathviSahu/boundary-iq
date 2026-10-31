import json
from typing import Dict, List, Optional, Any, Set, Tuple
from app.models.match import (
    Delivery, SnapshotState, BatterLiveStats, BowlerLiveStats,
    MatchMetadata, PlayerInfo, KeyMoment, WicketDetail
)
from app.models.fantasy import (
    PlayerFantasyScore, BreakdownItem, PlayerDelta,
    BallFantasyImpact, FantasyTeamConfig, OptimalCaptaincyComparison
)
from app.scoring.ruleset import RulesetConfig, DEFAULT_RULESET

PLAYER_ROLES_LOOKUP: Dict[str, str] = {
    # India 2024 Final
    "RG Sharma": "BAT",
    "V Kohli": "BAT",
    "RR Pant": "WK",
    "SA Yadav": "BAT",
    "AR Patel": "AR",
    "S Dube": "AR",
    "HH Pandya": "AR",
    "RA Jadeja": "AR",
    "Kuldeep Yadav": "BOWL",
    "Arshdeep Singh": "BOWL",
    "JJ Bumrah": "BOWL",
    # South Africa 2024 Final
    "RR Hendricks": "BAT",
    "Q de Kock": "WK",
    "AK Markram": "BAT",
    "T Stubbs": "BAT",
    "H Klaasen": "WK",
    "DA Miller": "BAT",
    "M Jansen": "AR",
    "KA Maharaj": "BOWL",
    "K Rabada": "BOWL",
    "A Nortje": "BOWL",
    "T Shamsi": "BOWL",
}

PLAYER_CREDITS_LOOKUP: Dict[str, float] = {
    "V Kohli": 9.5,
    "JJ Bumrah": 9.5,
    "RG Sharma": 9.0,
    "HH Pandya": 9.0,
    "Q de Kock": 9.0,
    "H Klaasen": 9.0,
    "SA Yadav": 9.0,
    "Arshdeep Singh": 8.5,
    "AR Patel": 8.5,
    "K Rabada": 8.5,
    "AK Markram": 8.5,
    "DA Miller": 8.5,
    "A Nortje": 8.5,
    "Kuldeep Yadav": 8.5,
    "KA Maharaj": 8.0,
    "RR Pant": 8.0,
    "S Dube": 8.0,
    "M Jansen": 8.0,
    "RA Jadeja": 8.0,
    "T Stubbs": 8.0,
    "RR Hendricks": 7.5,
    "T Shamsi": 7.5,
}

class ReplayEngine:
    def __init__(self, json_path: str, ruleset: Optional[RulesetConfig] = None):
        self.json_path = json_path
        self.ruleset = ruleset or DEFAULT_RULESET
        self.deliveries: List[Delivery] = []
        self.metadata: Optional[MatchMetadata] = None
        self.all_players: Set[str] = set()

        # Precomputed Snapshots for O(1) instant replay
        self.snapshots: List[SnapshotState] = []
        self.base_fantasy_snapshots: List[Dict[str, PlayerFantasyScore]] = []
        self.ball_deltas: List[BallFantasyImpact] = []
        self.key_moments: List[KeyMoment] = []

        self._parse_and_precompute()

    def _parse_and_precompute(self):
        with open(self.json_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

        info = raw.get("info", {})
        teams = info.get("teams", [])
        event = info.get("event", {})
        venue = info.get("venue", "Cricket Stadium")
        city = info.get("city", "")
        dates = info.get("dates", [])
        toss = info.get("toss", {})
        outcome = info.get("outcome", {})
        players_dict = info.get("players", {})

        roster: List[PlayerInfo] = []
        for t, plist in players_dict.items():
            for p in plist:
                self.all_players.add(p)
                roster.append(PlayerInfo(
                    name=p,
                    team=t,
                    role=PLAYER_ROLES_LOOKUP.get(p, "BAT"),
                    credits=PLAYER_CREDITS_LOOKUP.get(p, 8.5)
                ))

        # Flatten deliveries
        innings_list = raw.get("innings", [])
        delivery_idx = 0

        for inn_idx, inn in enumerate(innings_list):
            inn_num = inn_idx + 1
            batting_t = inn.get("team", "")
            bowling_t = teams[1] if batting_t == teams[0] else teams[0]

            for over_obj in inn.get("overs", []):
                over_num = over_obj.get("over", 0)
                over_dlvs = over_obj.get("deliveries", [])

                # Check maiden over status:
                # 1. Count legal deliveries (excluding wides and no-balls).
                # 2. Exclude runs not charged to bowler (byes and leg-byes).
                # 3. A maiden over requires a completed qualifying over (at least 6 legal deliveries bowled by a single bowler).
                legal_balls_in_over = 0
                bowler_runs_in_over = 0
                bowlers_in_over = set()
                for d in over_dlvs:
                    b_name = d.get("bowler", "")
                    if b_name:
                        bowlers_in_over.add(b_name)
                    r_bat = d.get("runs", {}).get("batter", 0)
                    ex = d.get("extras", {})
                    e_bowler = ex.get("wides", 0) + ex.get("noballs", 0)
                    bowler_runs_in_over += (r_bat + e_bowler)
                    if "wides" not in ex and "noballs" not in ex:
                        legal_balls_in_over += 1

                is_single_bowler = (len(bowlers_in_over) == 1)
                is_maiden_over = (legal_balls_in_over >= 6 and bowler_runs_in_over == 0 and is_single_bowler)

                for b_i, dlv in enumerate(over_dlvs):
                    batter = dlv.get("batter", "")
                    bowler = dlv.get("bowler", "")
                    non_striker = dlv.get("non_striker", "")
                    runs_obj = dlv.get("runs", {})
                    batter_runs = runs_obj.get("batter", 0)
                    extra_runs = runs_obj.get("extras", 0)
                    total_runs = runs_obj.get("total", 0)
                    raw_nb = runs_obj.get("non_boundary", False)
                    non_boundary = (raw_nb is True or raw_nb == 1 or str(raw_nb).lower() in ("true", "1"))

                    extras_obj = dlv.get("extras", {})
                    extra_type = list(extras_obj.keys())[0] if extras_obj else None

                    w_list = dlv.get("wickets", [])
                    is_wicket = len(w_list) > 0
                    parsed_wickets: List[WicketDetail] = []
                    all_fielders: List[str] = []
                    all_players_out: List[str] = []

                    for w_info in w_list:
                        w_kind = w_info.get("kind", "")
                        p_out = w_info.get("player_out", "")
                        w_fielders: List[str] = []
                        for fld in w_info.get("fielders", []):
                            if isinstance(fld, dict) and "name" in fld:
                                w_fielders.append(fld["name"])
                                if fld["name"] not in all_fielders:
                                    all_fielders.append(fld["name"])
                            elif isinstance(fld, str):
                                w_fielders.append(fld)
                                if fld not in all_fielders:
                                    all_fielders.append(fld)
                        if p_out:
                            all_players_out.append(p_out)
                        parsed_wickets.append(WicketDetail(
                            kind=w_kind,
                            player_out=p_out,
                            fielders=w_fielders
                        ))

                    wicket_kind = parsed_wickets[0].kind if parsed_wickets else None
                    player_out = parsed_wickets[0].player_out if len(parsed_wickets) == 1 else (", ".join(all_players_out) if all_players_out else None)

                    # Direct-hit run out verification:
                    # Cricsheet documents that fielders identify players involved in dismissal;
                    # it does not establish whether the run-out was a direct hit.
                    # Direct hit is only True if explicitly specified in source data (e.g. direct_hit flag).
                    # When evidence is unavailable, direct_hit remains None and direct-hit bonus is withheld.
                    direct_hit = None
                    if is_wicket and any(w.kind == "run out" for w in parsed_wickets):
                        for w_info in w_list:
                            if "direct_hit" in w_info:
                                direct_hit = bool(w_info["direct_hit"])
                                break
                            elif "directhit" in w_info:
                                direct_hit = bool(w_info["directhit"])
                                break

                    # Genuine boundaries: non_boundary 4s/6s (e.g. overthrows or all-run)
                    # award regular batter run points, but DO NOT receive boundary bonus points.
                    # Boundaries struck off legal balls or no-balls qualify if struck by batter.
                    is_four = (batter_runs == 4 and not non_boundary)
                    is_six = (batter_runs == 6 and not non_boundary)
                    is_dot = (total_runs == 0 and not is_wicket)
                    is_maiden_end = (is_maiden_over and b_i == len(over_dlvs) - 1)

                    over_display = f"{over_num}.{b_i + 1}"
                    summary = self._create_summary(
                        batter, bowler, batter_runs, extra_runs, extra_type,
                        is_wicket, wicket_kind, player_out, all_fielders,
                        non_boundary=non_boundary,
                        parsed_wickets=parsed_wickets
                    )

                    deliv_obj = Delivery(
                        index=delivery_idx,
                        innings=inn_num,
                        team_batting=batting_t,
                        team_bowling=bowling_t,
                        over=over_num,
                        ball_in_over=b_i + 1,
                        over_display=over_display,
                        batter=batter,
                        bowler=bowler,
                        non_striker=non_striker,
                        batter_runs=batter_runs,
                        extra_runs=extra_runs,
                        total_runs=total_runs,
                        extra_type=extra_type,
                        non_boundary=non_boundary,
                        is_wicket=is_wicket,
                        wicket_kind=wicket_kind,
                        player_out=player_out,
                        fielders=all_fielders,
                        direct_hit=direct_hit,
                        wickets=parsed_wickets,
                        is_four=is_four,
                        is_six=is_six,
                        is_dot=is_dot,
                        is_maiden_completing_ball=is_maiden_end,
                        summary=summary
                    )
                    self.deliveries.append(deliv_obj)
                    delivery_idx += 1

        self.metadata = MatchMetadata(
            match_id="ind_sa_t20wc_2024_final",
            event_name=f"{event.get('name', 'T20 World Cup')} - {event.get('stage', 'Final')}",
            venue=venue,
            city=city,
            dates=dates,
            teams=teams,
            toss=toss,
            outcome=outcome,
            total_deliveries=len(self.deliveries),
            players=players_dict,
            roster=roster
        )

        # Single forward-pass pre-computation of ALL snapshots
        self._build_snapshots_forward_pass()

    def _create_summary(self, batter: str, bowler: str, b_runs: int, e_runs: int,
                        e_type: Optional[str], is_wicket: bool,
                        w_kind: Optional[str], player_out: Optional[str],
                        fielders: List[str], non_boundary: bool = False,
                        parsed_wickets: Optional[List[WicketDetail]] = None) -> str:
        if is_wicket and parsed_wickets and len(parsed_wickets) > 1:
            outs = [f"{w.player_out} ({w.kind})" for w in parsed_wickets]
            return f"MULTIPLE WICKETS! {', '.join(outs)} off {bowler}!"
        if is_wicket:
            if w_kind == "caught":
                f_name = fielders[0] if fielders else "fielder"
                return f"WICKET! {bowler} to {player_out}, c {f_name} b {bowler}! OUT for {player_out}."
            elif w_kind in ("bowled", "lbw"):
                return f"WICKET! {bowler} to {player_out}, {w_kind.upper()}! Stumps shattered."
            elif w_kind == "run out":
                f_name = " & ".join(fielders) if fielders else "fielders"
                return f"RUN OUT! {player_out} dismissed by {f_name}."
            return f"WICKET! {player_out} out ({w_kind}) off {bowler}."
        if e_type:
            return f"{bowler} to {batter}, {e_runs} EXTRA ({e_type.upper()})."
        if b_runs == 6:
            if non_boundary:
                return f"{bowler} to {batter}, 6 runs taken (all-run / overthrows, non-boundary)."
            return f"MAXIMUM! {bowler} to {batter}, SIX runs launched into the stands!"
        if b_runs == 4:
            if non_boundary:
                return f"{bowler} to {batter}, 4 runs taken (all-run / overthrows, non-boundary)."
            return f"FOUR! {bowler} to {batter}, driven majestically to the boundary!"
        if b_runs == 0:
            return f"{bowler} to {batter}, no run. Beaten outside off."
        return f"{bowler} to {batter}, {b_runs} run{'s' if b_runs > 1 else ''}."

    def _build_snapshots_forward_pass(self):
        """
        Builds immutable snapshots in ONE forward pass (O(N) initialization).
        Once built, all replay operations (prev, next, slider, jump) are O(1).
        """
        inn1_total = 0
        inn1_wickets = 0
        inn1_legal_balls = 0

        # Cumulative trackers
        curr_inn = 1
        team_score = 0
        team_wickets = 0
        legal_balls = 0

        batters_stats: Dict[str, Dict[str, Any]] = {}
        bowlers_stats: Dict[str, Dict[str, Any]] = {}
        fielders_stats: Dict[str, Dict[str, int]] = {
            p: {"catches": 0, "stumpings": 0, "run_outs_direct": 0, "run_outs_shared": 0}
            for p in self.all_players
        }

        # Track milestone crossings so each is awarded EXACTLY ONCE
        awarded_milestones: Dict[str, Set[str]] = {p: set() for p in self.all_players}

        recent_balls_buffer: List[Dict[str, Any]] = []
        prev_player_scores: Dict[str, PlayerFantasyScore] = {}

        for idx, dlv in enumerate(self.deliveries):
            if dlv.innings != curr_inn:
                # Transition to innings 2
                curr_inn = dlv.innings
                team_score = 0
                team_wickets = 0
                legal_balls = 0
                recent_balls_buffer = []

            # Process wickets without silently ignoring subsequent wicket records
            active_wickets: List[WicketDetail] = dlv.wickets if dlv.wickets else (
                [WicketDetail(kind=dlv.wicket_kind or "", player_out=dlv.player_out or "", fielders=dlv.fielders)]
                if dlv.is_wicket else []
            )

            # Update match score
            team_score += dlv.total_runs
            if dlv.is_wicket:
                team_wickets += len(active_wickets)

            is_legal = dlv.extra_type not in ("wides", "noballs")
            if is_legal:
                legal_balls += 1

            if dlv.innings == 1:
                inn1_total += dlv.total_runs
                if dlv.is_wicket:
                    inn1_wickets += len(active_wickets)
                if is_legal:
                    inn1_legal_balls += 1

            # Update Batter
            b_name = dlv.batter
            if b_name not in batters_stats:
                batters_stats[b_name] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None}
            batters_stats[b_name]["runs"] += dlv.batter_runs
            if dlv.extra_type != "wides":
                batters_stats[b_name]["balls"] += 1
            if dlv.is_four:
                batters_stats[b_name]["fours"] += 1
            if dlv.is_six:
                batters_stats[b_name]["sixes"] += 1

            if dlv.is_wicket:
                for w_item in active_wickets:
                    p_out = w_item.player_out
                    if p_out:
                        if p_out not in batters_stats:
                            batters_stats[p_out] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None}
                        batters_stats[p_out]["is_out"] = True
                        batters_stats[p_out]["dismissal"] = w_item.kind

            # Update Bowler
            bw_name = dlv.bowler
            if bw_name not in bowlers_stats:
                bowlers_stats[bw_name] = {
                    "legal_balls": 0, "runs_conceded": 0, "wickets": 0,
                    "lbw_bowled": 0, "maidens": 0, "dot_balls": 0
                }
            bowler_extras = dlv.extra_runs if dlv.extra_type in ("wides", "noballs") else 0
            bowlers_stats[bw_name]["runs_conceded"] += (dlv.batter_runs + bowler_extras)
            if is_legal:
                bowlers_stats[bw_name]["legal_balls"] += 1
                # Dot ball bowled: legal ball with 0 runs conceded by bowler off bat or wide/noball
                if (dlv.batter_runs + bowler_extras) == 0:
                    bowlers_stats[bw_name]["dot_balls"] += 1

            if dlv.is_wicket:
                for w_item in active_wickets:
                    if w_item.kind not in ("run out", "retired hurt"):
                        bowlers_stats[bw_name]["wickets"] += 1
                        if w_item.kind in ("bowled", "lbw"):
                            bowlers_stats[bw_name]["lbw_bowled"] += 1
            if dlv.is_maiden_completing_ball:
                bowlers_stats[bw_name]["maidens"] += 1

            # Update Fielders
            if dlv.is_wicket:
                for w_item in active_wickets:
                    for fld in w_item.fielders:
                        if fld not in fielders_stats:
                            fielders_stats[fld] = {"catches": 0, "stumpings": 0, "run_outs_direct": 0, "run_outs_shared": 0}
                        if w_item.kind == "caught":
                            fielders_stats[fld]["catches"] += 1
                        elif w_item.kind == "stumped":
                            fielders_stats[fld]["stumpings"] += 1
                        elif w_item.kind == "run out":
                            # Cricsheet documents that the fielders list identifies fielders involved in a dismissal;
                            # it does not establish whether the run-out was a direct hit.
                            # Direct-hit bonus (+12 pts) requires verified source evidence (dlv.direct_hit is True).
                            # Otherwise, award standard run-out points (run_out_shared: 6 pts) without overstating points.
                            if dlv.direct_hit is True:
                                fielders_stats[fld]["run_outs_direct"] += 1
                            else:
                                fielders_stats[fld]["run_outs_shared"] += 1

            # Recent deliveries buffer
            recent_balls_buffer.append({
                "index": dlv.index,
                "over_display": dlv.over_display,
                "total_runs": dlv.total_runs,
                "is_wicket": dlv.is_wicket,
                "is_four": dlv.is_four,
                "is_six": dlv.is_six,
                "extra_type": dlv.extra_type
            })

            # Check Milestone Crossings on this delivery (Awarded EXACTLY ONCE)
            milestone_awarded_on_ball: List[str] = []
            
            # 1. Batting milestones: 25, 50, 75, 100 runs
            cur_b_runs = batters_stats[b_name]["runs"]
            if cur_b_runs >= 100 and "100_runs" not in awarded_milestones[b_name]:
                awarded_milestones[b_name].add("100_runs")
                milestone_awarded_on_ball.append(f"{b_name} reached Century (100+ runs)!")
            elif cur_b_runs >= 75 and "75_runs" not in awarded_milestones[b_name]:
                awarded_milestones[b_name].add("75_runs")
                milestone_awarded_on_ball.append(f"{b_name} reached 75 Runs Milestone!")
            elif cur_b_runs >= 50 and "50_runs" not in awarded_milestones[b_name]:
                awarded_milestones[b_name].add("50_runs")
                milestone_awarded_on_ball.append(f"{b_name} reached Half-Century (50+ runs)!")
            elif cur_b_runs >= 25 and "25_runs" not in awarded_milestones[b_name]:
                awarded_milestones[b_name].add("25_runs")
                milestone_awarded_on_ball.append(f"{b_name} crossed 25 Runs Milestone!")

            # 2. Bowling milestones: 3, 4, 5 wickets
            cur_bw_w = bowlers_stats[bw_name]["wickets"]
            if cur_bw_w >= 5 and "5_wickets" not in awarded_milestones[bw_name]:
                awarded_milestones[bw_name].add("5_wickets")
                milestone_awarded_on_ball.append(f"{bw_name} took 5-Wicket Haul (+12 pts)!")
            elif cur_bw_w == 4 and "4_wickets" not in awarded_milestones[bw_name]:
                awarded_milestones[bw_name].add("4_wickets")
                milestone_awarded_on_ball.append(f"{bw_name} took 4-Wicket Haul (+8 pts)!")
            elif cur_bw_w == 3 and "3_wickets" not in awarded_milestones[bw_name]:
                awarded_milestones[bw_name].add("3_wickets")
                milestone_awarded_on_ball.append(f"{bw_name} took 3-Wicket Haul (+4 pts)!")

            # 3. Maiden milestone
            if dlv.is_maiden_completing_ball:
                milestone_awarded_on_ball.append(f"{bw_name} completed a Maiden Over (+12 pts)!")

            # 4. Duck penalty milestone
            if dlv.is_wicket:
                for w_item in active_wickets:
                    p_out = w_item.player_out
                    if p_out:
                        role_out = PLAYER_ROLES_LOOKUP.get(p_out, "BAT")
                        p_runs = batters_stats[p_out]["runs"]
                        if p_runs == 0 and role_out in ("BAT", "WK", "AR") and "duck" not in awarded_milestones[p_out]:
                            awarded_milestones[p_out].add("duck")
                            milestone_awarded_on_ball.append(f"{p_out} dismissed for Duck (-2 pts penalty)")

            # 5. Fielding 3-catch milestone
            if dlv.is_wicket:
                for w_item in active_wickets:
                    if w_item.kind == "caught":
                        for fld in w_item.fielders:
                            if fielders_stats[fld]["catches"] >= 3 and "3_catches" not in awarded_milestones[fld]:
                                awarded_milestones[fld].add("3_catches")
                                milestone_awarded_on_ball.append(f"{fld} completed 3 Catches (+4 pts bonus)!")

            # Calculate base player fantasy points at this delivery
            current_fantasy_scores: Dict[str, PlayerFantasyScore] = {}
            for p in self.all_players:
                score = self._compute_base_fantasy_points(
                    player_name=p,
                    batters_stats=batters_stats,
                    bowlers_stats=bowlers_stats,
                    fielders_stats=fielders_stats,
                    awarded_milestones=awarded_milestones
                )
                current_fantasy_scores[p] = score

            self.base_fantasy_snapshots.append(current_fantasy_scores)

            # Key moment detection
            key_moment = None
            is_km = False
            if dlv.is_wicket:
                is_km = True
                category = "wicket"
                title = f"Wicket: {dlv.player_out} dismissed!"
                subtitle = dlv.summary
                points_hl = f"+{self.ruleset.wicket_normal:.0f} pts for {dlv.bowler}"
                if dlv.wicket_kind in ("bowled", "lbw"):
                    points_hl += " (+8 Bowled/LBW bonus)"
                key_moment = KeyMoment(
                    delivery_index=idx,
                    over_display=dlv.over_display,
                    category=category,
                    title=title,
                    subtitle=subtitle,
                    points_headline=points_hl
                )
            elif dlv.is_six:
                is_km = True
                total_six_pts = int(6 + self.ruleset.six_bonus)
                key_moment = KeyMoment(
                    delivery_index=idx,
                    over_display=dlv.over_display,
                    category="boundary",
                    title=f"MAXIMUM! 6 by {dlv.batter}",
                    subtitle=dlv.summary,
                    points_headline=f"+{total_six_pts} pts for {dlv.batter} (6 runs + {self.ruleset.six_bonus:.0f} six bonus)"
                )
            elif dlv.is_four:
                is_km = True
                total_four_pts = int(4 + self.ruleset.boundary_four_bonus)
                key_moment = KeyMoment(
                    delivery_index=idx,
                    over_display=dlv.over_display,
                    category="boundary",
                    title=f"FOUR by {dlv.batter}",
                    subtitle=dlv.summary,
                    points_headline=f"+{total_four_pts} pts for {dlv.batter} (4 runs + {self.ruleset.boundary_four_bonus:.0f} four bonus)"
                )
            elif milestone_awarded_on_ball:
                is_km = True
                key_moment = KeyMoment(
                    delivery_index=idx,
                    over_display=dlv.over_display,
                    category="milestone",
                    title="Fantasy Milestone Crossed!",
                    subtitle="; ".join(milestone_awarded_on_ball),
                    points_headline="Milestone bonus awarded"
                )
            elif idx == len(self.deliveries) - 1:
                is_km = True
                key_moment = KeyMoment(
                    delivery_index=idx,
                    over_display=dlv.over_display,
                    category="climax",
                    title="Match Finale: India wins T20 World Cup!",
                    subtitle="Final delivery defended by Hardik Pandya. India wins by 7 runs!",
                    points_headline="World Cup Final Victory!"
                )

            if key_moment:
                self.key_moments.append(key_moment)

            # Scoreboard calculations
            completed_ov = legal_balls // 6
            rem_b = legal_balls % 6
            ov_disp = f"{completed_ov}.{rem_b}"
            ov_fl = completed_ov + (rem_b / 6.0)
            crr = round(team_score / ov_fl, 2) if ov_fl > 0 else 0.0

            target = (inn1_total + 1) if curr_inn == 2 else None
            rrr = None
            runs_needed = None
            balls_remaining = None

            inn1_comp_ov = inn1_legal_balls // 6
            inn1_rem_b = inn1_legal_balls % 6
            inn1_ov_disp = f"{inn1_comp_ov}.{inn1_rem_b}"
            inn1_team = self.deliveries[0].team_batting if self.deliveries else "India"

            first_innings_team = inn1_team if curr_inn == 2 else None
            first_innings_score = inn1_total if curr_inn == 2 else None
            first_innings_wickets = inn1_wickets if curr_inn == 2 else None
            first_innings_overs = inn1_ov_disp if curr_inn == 2 else None
            first_innings_summary = f"{inn1_team} {inn1_total}/{inn1_wickets} ({inn1_ov_disp} ov)" if curr_inn == 2 else None

            if curr_inn == 2 and target is not None:
                runs_needed = max(0, target - team_score)
                balls_remaining = max(0, 120 - legal_balls)
                if balls_remaining > 0 and runs_needed > 0:
                    rrr = round((runs_needed / balls_remaining) * 6.0, 2)
                elif runs_needed == 0:
                    rrr = 0.0

            # Match status
            if idx == len(self.deliveries) - 1:
                status_txt = "Match Completed: India won by 7 runs (ICC T20 World Cup Champions 2024)"
            elif curr_inn == 1:
                status_txt = f"1st Innings: {dlv.team_batting} batting ({team_score}/{team_wickets})"
            else:
                if runs_needed is not None and runs_needed > 0:
                    status_txt = f"{dlv.team_batting} need {runs_needed} runs from {balls_remaining} balls"
                else:
                    status_txt = "Target Achieved!"

            # Striker & Non-striker stats
            s_name = dlv.batter
            s_data = batters_stats.get(s_name, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None})
            s_sr = round((s_data["runs"] / s_data["balls"]) * 100, 1) if s_data["balls"] > 0 else 0.0
            striker_stats = BatterLiveStats(
                name=s_name,
                runs=s_data["runs"],
                balls=s_data["balls"],
                fours=s_data["fours"],
                sixes=s_data["sixes"],
                strike_rate=s_sr,
                is_out=s_data["is_out"],
                dismissal_desc=s_data["dismissal"]
            )

            ns_name = dlv.non_striker
            ns_data = batters_stats.get(ns_name, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None})
            ns_sr = round((ns_data["runs"] / ns_data["balls"]) * 100, 1) if ns_data["balls"] > 0 else 0.0
            non_striker_stats = BatterLiveStats(
                name=ns_name,
                runs=ns_data["runs"],
                balls=ns_data["balls"],
                fours=ns_data["fours"],
                sixes=ns_data["sixes"],
                strike_rate=ns_sr,
                is_out=ns_data["is_out"],
                dismissal_desc=ns_data["dismissal"]
            )

            # Bowler stats
            bw_name = dlv.bowler
            bw_data = bowlers_stats.get(bw_name, {
                "legal_balls": 0, "runs_conceded": 0, "wickets": 0,
                "lbw_bowled": 0, "maidens": 0, "dot_balls": 0
            })
            b_c_ov = bw_data["legal_balls"] // 6
            b_r_b = bw_data["legal_balls"] % 6
            b_ov_disp = b_c_ov + (b_r_b / 10.0)
            b_ov_fl = b_c_ov + (b_r_b / 6.0)
            b_econ = round(bw_data["runs_conceded"] / b_ov_fl, 2) if b_ov_fl > 0 else 0.0

            bowler_stats = BowlerLiveStats(
                name=bw_name,
                overs=b_ov_disp,
                legal_balls=bw_data["legal_balls"],
                maidens=bw_data["maidens"],
                runs_conceded=bw_data["runs_conceded"],
                wickets=bw_data["wickets"],
                economy=b_econ
            )

            # Pre-compute Ball Fantasy Delta compared to prev delivery
            ball_impact = self._compute_ball_delta_precomputed(
                idx=idx,
                dlv=dlv,
                current_scores=current_fantasy_scores,
                prev_scores=prev_player_scores
            )
            self.ball_deltas.append(ball_impact)
            prev_player_scores = current_fantasy_scores

            # Create immutable Snapshot
            snapshot = SnapshotState(
                delivery_index=idx,
                over_display=dlv.over_display,
                innings=curr_inn,
                batting_team=dlv.team_batting,
                bowling_team=dlv.team_bowling,
                team_score=team_score,
                team_wickets=team_wickets,
                overs_display=ov_disp,
                legal_balls_bowled=legal_balls,
                run_rate=crr,
                target=target,
                required_run_rate=rrr,
                runs_needed=runs_needed,
                balls_remaining=balls_remaining,
                first_innings_team=first_innings_team,
                first_innings_score=first_innings_score,
                first_innings_wickets=first_innings_wickets,
                first_innings_overs=first_innings_overs,
                first_innings_summary=first_innings_summary,
                striker=striker_stats,
                non_striker=non_striker_stats,
                bowler=bowler_stats,
                recent_balls=list(recent_balls_buffer[-12:]),
                match_status=status_txt,
                is_key_moment=is_km,
                key_moment_info=key_moment,
                delivery_event=dlv
            )
            self.snapshots.append(snapshot)

    def _compute_base_fantasy_points(
        self,
        player_name: str,
        batters_stats: Dict[str, Dict[str, Any]],
        bowlers_stats: Dict[str, Dict[str, Any]],
        fielders_stats: Dict[str, Dict[str, int]],
        awarded_milestones: Dict[str, Set[str]]
    ) -> PlayerFantasyScore:
        role = PLAYER_ROLES_LOOKUP.get(player_name, "BAT")
        team = ""
        for t, plist in self.metadata.players.items():
            if player_name in plist:
                team = t
                break

        breakdown: List[BreakdownItem] = []

        # 1. Starting XI Bonus (+4 pts)
        breakdown.append(BreakdownItem(
            category="general",
            label="Starting XI Announced",
            count=1,
            points_each=self.ruleset.starting_xi,
            total_points=self.ruleset.starting_xi
        ))

        # 2. Batting Points
        b_data = batters_stats.get(player_name, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None})
        runs = b_data["runs"]
        balls = b_data["balls"]
        fours = b_data["fours"]
        sixes = b_data["sixes"]

        if runs > 0:
            breakdown.append(BreakdownItem(
                category="batting",
                label=f"Runs Scored ({runs})",
                count=runs,
                points_each=self.ruleset.run,
                total_points=runs * self.ruleset.run
            ))
        if fours > 0:
            breakdown.append(BreakdownItem(
                category="batting",
                label=f"Boundary 4s ({fours})",
                count=fours,
                points_each=self.ruleset.boundary_four_bonus,
                total_points=fours * self.ruleset.boundary_four_bonus
            ))
        if sixes > 0:
            breakdown.append(BreakdownItem(
                category="batting",
                label=f"Boundary 6s ({sixes})",
                count=sixes,
                points_each=self.ruleset.six_bonus,
                total_points=sixes * self.ruleset.six_bonus
            ))

        # Non-stacking Batting Milestones: Century (16) > 75 (12) > 50 (8) > 25 (4)
        p_milestones = awarded_milestones[player_name]
        if "100_runs" in p_milestones:
            breakdown.append(BreakdownItem(
                category="batting",
                label="Century Bonus (100+)",
                count=1,
                points_each=self.ruleset.century_bonus,
                total_points=self.ruleset.century_bonus
            ))
        elif "75_runs" in p_milestones:
            breakdown.append(BreakdownItem(
                category="batting",
                label="75-Run Milestone Bonus",
                count=1,
                points_each=self.ruleset.seventy_five_run_bonus,
                total_points=self.ruleset.seventy_five_run_bonus
            ))
        elif "50_runs" in p_milestones:
            breakdown.append(BreakdownItem(
                category="batting",
                label="Half-Century Bonus (50+)",
                count=1,
                points_each=self.ruleset.half_century_bonus,
                total_points=self.ruleset.half_century_bonus
            ))
        elif "25_runs" in p_milestones:
            breakdown.append(BreakdownItem(
                category="batting",
                label="25-Run Milestone Bonus",
                count=1,
                points_each=self.ruleset.twenty_five_run_bonus,
                total_points=self.ruleset.twenty_five_run_bonus
            ))

        # Duck penalty
        if "duck" in p_milestones:
            breakdown.append(BreakdownItem(
                category="batting",
                label="Dismissal for Duck",
                count=1,
                points_each=self.ruleset.duck_penalty,
                total_points=self.ruleset.duck_penalty
            ))

        # Strike Rate (Min 10 balls, not applicable for pure BOWL)
        if balls >= self.ruleset.strike_rate.min_balls and role != "BOWL":
            sr = (runs / balls) * 100.0
            sr_pts = 0.0
            sr_label = ""
            if sr > 170.0:
                sr_pts = self.ruleset.strike_rate.tier_above_170
                sr_label = f"Strike Rate Bonus (>170: {sr:.1f})"
            elif 150.01 <= sr <= 170.0:
                sr_pts = self.ruleset.strike_rate.tier_150_to_170
                sr_label = f"Strike Rate Bonus (150-170: {sr:.1f})"
            elif 130.0 <= sr <= 150.0:
                sr_pts = self.ruleset.strike_rate.tier_130_to_150
                sr_label = f"Strike Rate Bonus (130-150: {sr:.1f})"
            elif 60.0 <= sr <= 70.0:
                sr_pts = self.ruleset.strike_rate.tier_60_to_70
                sr_label = f"Strike Rate Penalty (60-70: {sr:.1f})"
            elif 50.0 <= sr < 60.0:
                sr_pts = self.ruleset.strike_rate.tier_50_to_60
                sr_label = f"Strike Rate Penalty (50-60: {sr:.1f})"
            elif sr < 50.0:
                sr_pts = self.ruleset.strike_rate.tier_below_50
                sr_label = f"Strike Rate Penalty (<50: {sr:.1f})"

            if sr_pts != 0.0:
                breakdown.append(BreakdownItem(
                    category="batting",
                    label=sr_label,
                    count=1,
                    points_each=sr_pts,
                    total_points=sr_pts
                ))

        # 3. Bowling Points
        bw_data = bowlers_stats.get(player_name, {
            "legal_balls": 0, "runs_conceded": 0, "wickets": 0,
            "lbw_bowled": 0, "maidens": 0, "dot_balls": 0
        })
        w = bw_data["wickets"]
        lbw_b = bw_data["lbw_bowled"]
        maidens = bw_data["maidens"]
        dots = bw_data["dot_balls"]
        b_balls = bw_data["legal_balls"]
        b_runs_c = bw_data["runs_conceded"]

        if w > 0:
            breakdown.append(BreakdownItem(
                category="bowling",
                label=f"Wickets Taken ({w})",
                count=w,
                points_each=self.ruleset.wicket_normal,
                total_points=w * self.ruleset.wicket_normal
            ))
        if lbw_b > 0:
            breakdown.append(BreakdownItem(
                category="bowling",
                label=f"Bowled / LBW Bonus ({lbw_b})",
                count=lbw_b,
                points_each=self.ruleset.lbw_bowled_bonus,
                total_points=lbw_b * self.ruleset.lbw_bowled_bonus
            ))
        if dots > 0:
            breakdown.append(BreakdownItem(
                category="bowling",
                label=f"Dot Balls Bowled ({dots})",
                count=dots,
                points_each=self.ruleset.dot_ball_bowled,
                total_points=dots * self.ruleset.dot_ball_bowled
            ))

        # Bowling milestone bonuses (non-stacking: 5W [12] > 4W [8] > 3W [4])
        if "5_wickets" in p_milestones:
            breakdown.append(BreakdownItem(
                category="bowling",
                label="5-Wicket Haul Bonus",
                count=1,
                points_each=self.ruleset.five_wicket_bonus,
                total_points=self.ruleset.five_wicket_bonus
            ))
        elif "4_wickets" in p_milestones:
            breakdown.append(BreakdownItem(
                category="bowling",
                label="4-Wicket Haul Bonus",
                count=1,
                points_each=self.ruleset.four_wicket_bonus,
                total_points=self.ruleset.four_wicket_bonus
            ))
        elif "3_wickets" in p_milestones:
            breakdown.append(BreakdownItem(
                category="bowling",
                label="3-Wicket Haul Bonus",
                count=1,
                points_each=self.ruleset.three_wicket_bonus,
                total_points=self.ruleset.three_wicket_bonus
            ))

        if maidens > 0:
            breakdown.append(BreakdownItem(
                category="bowling",
                label=f"Maiden Overs ({maidens})",
                count=maidens,
                points_each=self.ruleset.maiden_over,
                total_points=maidens * self.ruleset.maiden_over
            ))

        # Economy rate bonus/penalty (min 12 legal balls = 2 overs)
        if b_balls >= self.ruleset.economy_rate.min_legal_balls:
            ov_fl = b_balls / 6.0
            econ = b_runs_c / ov_fl
            econ_pts = 0.0
            econ_label = ""
            if econ < 5.0:
                econ_pts = self.ruleset.economy_rate.tier_below_5
                econ_label = f"Economy Bonus (<5.0: {econ:.2f})"
            elif 5.0 <= econ < 6.0:
                econ_pts = self.ruleset.economy_rate.tier_5_to_6
                econ_label = f"Economy Bonus (5-6: {econ:.2f})"
            elif 6.0 <= econ <= 7.0:
                econ_pts = self.ruleset.economy_rate.tier_6_to_7
                econ_label = f"Economy Bonus (6-7: {econ:.2f})"
            elif 10.0 <= econ <= 11.0:
                econ_pts = self.ruleset.economy_rate.tier_10_to_11
                econ_label = f"Economy Penalty (10-11: {econ:.2f})"
            elif 11.0 < econ <= 12.0:
                econ_pts = self.ruleset.economy_rate.tier_11_to_12
                econ_label = f"Economy Penalty (11-12: {econ:.2f})"
            elif econ > 12.0:
                econ_pts = self.ruleset.economy_rate.tier_above_12
                econ_label = f"Economy Penalty (>12.0: {econ:.2f})"

            if econ_pts != 0.0:
                breakdown.append(BreakdownItem(
                    category="bowling",
                    label=econ_label,
                    count=1,
                    points_each=econ_pts,
                    total_points=econ_pts
                ))

        # 4. Fielding Points
        f_data = fielders_stats.get(player_name, {"catches": 0, "stumpings": 0, "run_outs_direct": 0, "run_outs_shared": 0})
        catches = f_data["catches"]
        stumpings = f_data["stumpings"]
        ro_dir = f_data["run_outs_direct"]
        ro_sh = f_data["run_outs_shared"]

        if catches > 0:
            breakdown.append(BreakdownItem(
                category="fielding",
                label=f"Catches Taken ({catches})",
                count=catches,
                points_each=self.ruleset.catch,
                total_points=catches * self.ruleset.catch
            ))
            if "3_catches" in p_milestones:
                breakdown.append(BreakdownItem(
                    category="fielding",
                    label="3 Catch Bonus",
                    count=1,
                    points_each=self.ruleset.three_catch_bonus,
                    total_points=self.ruleset.three_catch_bonus
                ))

        if stumpings > 0:
            breakdown.append(BreakdownItem(
                category="fielding",
                label=f"Stumpings ({stumpings})",
                count=stumpings,
                points_each=self.ruleset.stumping,
                total_points=stumpings * self.ruleset.stumping
            ))
        if ro_dir > 0:
            breakdown.append(BreakdownItem(
                category="fielding",
                label=f"Direct Run Outs ({ro_dir})",
                count=ro_dir,
                points_each=self.ruleset.run_out_direct,
                total_points=ro_dir * self.ruleset.run_out_direct
            ))
        if ro_sh > 0:
            breakdown.append(BreakdownItem(
                category="fielding",
                label=f"Run Outs ({ro_sh})",
                count=ro_sh,
                points_each=self.ruleset.run_out_shared,
                total_points=ro_sh * self.ruleset.run_out_shared
            ))

        raw_sum = sum(i.total_points for i in breakdown)
        return PlayerFantasyScore(
            player_name=player_name,
            team=team,
            role=role,
            is_captain=False,
            is_vice_captain=False,
            multiplier=1.0,
            raw_points=round(raw_sum, 1),
            total_points=round(raw_sum, 1),
            breakdown=breakdown,
            recent_delta=0.0
        )

    def _compute_ball_delta_precomputed(
        self,
        idx: int,
        dlv: Delivery,
        current_scores: Dict[str, PlayerFantasyScore],
        prev_scores: Dict[str, PlayerFantasyScore]
    ) -> BallFantasyImpact:
        player_deltas: List[PlayerDelta] = []
        is_legal = dlv.extra_type not in ("wides", "noballs")
        bowler_extras = dlv.extra_runs if dlv.extra_type in ("wides", "noballs") else 0

        active_wickets: List[WicketDetail] = dlv.wickets if dlv.wickets else (
            [WicketDetail(kind=dlv.wicket_kind or "", player_out=dlv.player_out or "", fielders=dlv.fielders)]
            if dlv.is_wicket else []
        )

        for p, cur_score in current_scores.items():
            prev_tot = prev_scores[p].total_points if p in prev_scores else self.ruleset.starting_xi
            diff = round(cur_score.total_points - prev_tot, 1)

            if abs(diff) > 0.001:
                category = "general"
                reasons: List[str] = []

                if p == dlv.batter:
                    category = "batting"
                    if dlv.batter_runs > 0:
                        reasons.append(f"+{dlv.batter_runs} run(s)")
                    if dlv.is_four:
                        reasons.append(f"Boundary 4 bonus (+{self.ruleset.boundary_four_bonus:.0f})")
                    if dlv.is_six:
                        reasons.append(f"Boundary 6 bonus (+{self.ruleset.six_bonus:.0f})")

                if p == dlv.bowler:
                    category = "bowling"
                    if is_legal and (dlv.batter_runs + bowler_extras) == 0:
                        reasons.append(f"Dot ball bowled (+{self.ruleset.dot_ball_bowled:.0f})")
                    if dlv.is_wicket:
                        for w_item in active_wickets:
                            if w_item.kind not in ("run out", "retired hurt"):
                                reasons.append(f"Wicket taken (+{self.ruleset.wicket_normal:.0f})")
                                if w_item.kind in ("bowled", "lbw"):
                                    reasons.append(f"Bowled/LBW bonus (+{self.ruleset.lbw_bowled_bonus:.0f})")
                    if dlv.is_maiden_completing_ball:
                        reasons.append(f"Maiden over (+{self.ruleset.maiden_over:.0f})")

                if dlv.is_wicket:
                    for w_item in active_wickets:
                        if p in w_item.fielders:
                            category = "fielding"
                            if w_item.kind == "caught":
                                reasons.append(f"Catch (+{self.ruleset.catch:.0f})")
                            elif w_item.kind == "stumped":
                                reasons.append(f"Stumping (+{self.ruleset.stumping:.0f})")
                            elif w_item.kind == "run out":
                                if dlv.direct_hit is True:
                                    reasons.append(f"Direct hit run out (+{self.ruleset.run_out_direct:.0f})")
                                else:
                                    reasons.append(f"Run out (+{self.ruleset.run_out_shared:.0f}, direct-hit unverified)")

                if dlv.is_wicket and any(p == w_item.player_out for w_item in active_wickets):
                    category = "batting"
                    reasons.append("Dismissed")

                reason_str = ", ".join(reasons) if reasons else "Fantasy point adjustment"

                player_deltas.append(PlayerDelta(
                    player_name=p,
                    team=cur_score.team,
                    reason=reason_str,
                    category=category,
                    raw_delta=diff,
                    multiplier=1.0,
                    net_delta=diff,
                    previous_total=round(prev_tot, 1),
                    new_total=cur_score.total_points,
                    is_captain=False,
                    is_vice_captain=False
                ))

        if player_deltas:
            d_strs = [f"{d.player_name} ({'+' if d.net_delta > 0 else ''}{d.net_delta} pts)" for d in player_deltas]
            summary = f"Over {dlv.over_display}: " + "; ".join(d_strs)
        else:
            summary = f"Over {dlv.over_display}: No fantasy points earned on this delivery."

        return BallFantasyImpact(
            delivery_index=idx,
            over_display=dlv.over_display,
            player_deltas=player_deltas,
            fantasy_team_total=0.0,
            fantasy_team_delta=0.0,
            summary_sentence=summary
        )

    # --- O(1) Snapshot Retrieval Functions ---

    def get_snapshot(self, index: int) -> SnapshotState:
        """O(1) lookup of pre-computed snapshot."""
        if not self.snapshots:
            raise ValueError("Replay snapshots have not been built")
        clamped = max(0, min(index, len(self.snapshots) - 1))
        return self.snapshots[clamped]

    def get_fantasy_scores_for_team(
        self,
        index: int,
        team_config: FantasyTeamConfig
    ) -> Tuple[Dict[str, PlayerFantasyScore], BallFantasyImpact, float, float]:
        """
        O(1) retrieval of base player points, applying Captain & Vice-Captain multipliers
        consistently to the user's selected fantasy squad without mutating base records.
        """
        clamped = max(0, min(index, len(self.base_fantasy_snapshots) - 1))
        base_scores = self.base_fantasy_snapshots[clamped]
        base_delta = self.ball_deltas[clamped]

        # Calculate squad scores with multipliers
        squad_scores: Dict[str, PlayerFantasyScore] = {}
        c_name = team_config.captain
        vc_name = team_config.vice_captain
        team_total = 0.0
        team_delta = 0.0

        for p_name, base_p in base_scores.items():
            is_c = (p_name == c_name)
            is_vc = (p_name == vc_name)

            mult = 1.0
            if is_c:
                mult = self.ruleset.captain_multiplier
            elif is_vc:
                mult = self.ruleset.vice_captain_multiplier

            tot_pts = round(base_p.raw_points * mult, 1)

            squad_scores[p_name] = PlayerFantasyScore(
                player_name=base_p.player_name,
                team=base_p.team,
                role=base_p.role,
                is_captain=is_c,
                is_vice_captain=is_vc,
                multiplier=mult,
                raw_points=base_p.raw_points,
                total_points=tot_pts,
                breakdown=base_p.breakdown,
                recent_delta=0.0
            )

            if p_name in team_config.selected_players:
                team_total += tot_pts

        # Update player deltas for team
        adjusted_deltas: List[PlayerDelta] = []
        for d in base_delta.player_deltas:
            is_c = (d.player_name == c_name)
            is_vc = (d.player_name == vc_name)
            mult = 1.0
            if is_c:
                mult = self.ruleset.captain_multiplier
            elif is_vc:
                mult = self.ruleset.vice_captain_multiplier

            adj_net = round(d.raw_delta * mult, 1)
            adj_prev = round(d.previous_total * mult, 1)
            adj_new = round(d.new_total * mult, 1)

            adjusted_deltas.append(PlayerDelta(
                player_name=d.player_name,
                team=d.team,
                reason=d.reason,
                category=d.category,
                raw_delta=d.raw_delta,
                multiplier=mult,
                net_delta=adj_net,
                previous_total=adj_prev,
                new_total=adj_new,
                is_captain=is_c,
                is_vice_captain=is_vc
            ))

            if d.player_name in team_config.selected_players:
                team_delta += adj_net

        adjusted_delta_impact = BallFantasyImpact(
            delivery_index=base_delta.delivery_index,
            over_display=base_delta.over_display,
            player_deltas=adjusted_deltas,
            fantasy_team_total=round(team_total, 1),
            fantasy_team_delta=round(team_delta, 1),
            summary_sentence=base_delta.summary_sentence
        )

        return squad_scores, adjusted_delta_impact, round(team_total, 1), round(team_delta, 1)

    def get_optimal_captaincy(
        self, delivery_index: int, team_config: FantasyTeamConfig
    ) -> OptimalCaptaincyComparison:
        """Calculate retrospective optimal captain & vice-captain combination for user squad."""
        idx = min(max(0, delivery_index), len(self.base_fantasy_snapshots) - 1)
        base_scores = self.base_fantasy_snapshots[idx]

        squad_players = [p for p in team_config.selected_players if p in base_scores]
        if not squad_players:
            squad_players = list(base_scores.keys())[:11]

        base_sum = sum(base_scores[p].raw_points for p in squad_players)

        curr_c = team_config.captain if team_config.captain in squad_players else squad_players[0]
        remaining = [p for p in squad_players if p != curr_c]
        curr_vc = team_config.vice_captain if team_config.vice_captain in remaining else (remaining[0] if remaining else curr_c)

        curr_c_raw = base_scores[curr_c].raw_points if curr_c in base_scores else 0.0
        curr_vc_raw = base_scores[curr_vc].raw_points if curr_vc in base_scores else 0.0

        c_mult = self.ruleset.captain_multiplier
        vc_mult = self.ruleset.vice_captain_multiplier

        curr_c_pts = round(curr_c_raw * c_mult, 1)
        curr_vc_pts = round(curr_vc_raw * vc_mult, 1)
        current_combo_points = round(curr_c_pts + curr_vc_pts, 1)
        current_team_total = round(base_sum + (c_mult - 1.0) * curr_c_raw + (vc_mult - 1.0) * curr_vc_raw, 1)

        sorted_players = sorted(squad_players, key=lambda p: base_scores[p].raw_points, reverse=True)
        opt_c = sorted_players[0]
        opt_vc = sorted_players[1] if len(sorted_players) > 1 else sorted_players[0]

        opt_c_raw = base_scores[opt_c].raw_points
        opt_vc_raw = base_scores[opt_vc].raw_points

        opt_c_pts = round(opt_c_raw * c_mult, 1)
        opt_vc_pts = round(opt_vc_raw * vc_mult, 1)
        optimal_combo_points = round(opt_c_pts + opt_vc_pts, 1)
        optimal_team_total = round(base_sum + (c_mult - 1.0) * opt_c_raw + (vc_mult - 1.0) * opt_vc_raw, 1)
        point_diff = round(optimal_team_total - current_team_total, 1)

        is_already_optimal = (point_diff <= 0.0) or (opt_c == curr_c and opt_vc == curr_vc)
        if is_already_optimal:
            point_diff = 0.0
            summary = f"Peak Captaincy! Your C/VC combo ({curr_c} & {curr_vc}) is maximizing points ({current_combo_points} pts)."
        else:
            summary = (
                f"What-If: {opt_c} (C, {opt_c_pts} pts) & {opt_vc} (VC, {opt_vc_pts} pts) "
                f"would yield +{point_diff} more pts so far."
            )

        return OptimalCaptaincyComparison(
            current_captain=curr_c,
            current_vice_captain=curr_vc,
            current_combo_points=current_combo_points,
            optimal_captain=opt_c,
            optimal_vice_captain=opt_vc,
            optimal_combo_points=optimal_combo_points,
            optimal_team_total=optimal_team_total,
            point_difference=point_diff,
            is_already_optimal=is_already_optimal,
            summary=summary
        )

    def get_key_moments(self, category: Optional[str] = None) -> List[KeyMoment]:
        if not category or category.lower() == 'all':
            return self.key_moments
        cat_lower = category.lower()
        if cat_lower == 'wickets':
            return [m for m in self.key_moments if m.category == 'wicket']
        if cat_lower == 'boundaries':
            return [m for m in self.key_moments if m.category == 'boundary']
        if cat_lower in ('milestones', 'fantasy milestones'):
            return [m for m in self.key_moments if m.category in ('milestone', 'climax')]
        return [m for m in self.key_moments if m.category == cat_lower]
