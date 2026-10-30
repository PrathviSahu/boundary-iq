import json
import os
from typing import Dict, List, Optional, Tuple, Any
from app.models.match import (
    Delivery, ScoreboardState, BatterLiveStats, BowlerLiveStats,
    MatchMetadata, PlayerInfo, WicketDetail
)

PLAYER_ROLES: Dict[str, str] = {
    # Pakistan
    "Mohammad Rizwan": "WK",
    "Babar Azam": "BAT",
    "Shan Masood": "BAT",
    "Iftikhar Ahmed": "AR",
    "Shadab Khan": "AR",
    "Haider Ali": "BAT",
    "Mohammad Nawaz": "AR",
    "Asif Ali": "BAT",
    "Shaheen Shah Afridi": "BOWL",
    "Haris Rauf": "BOWL",
    "Naseem Shah": "BOWL",
    # India
    "KL Rahul": "BAT",
    "RG Sharma": "BAT",
    "V Kohli": "BAT",
    "SA Yadav": "BAT",
    "AR Patel": "AR",
    "HH Pandya": "AR",
    "KD Karthik": "WK",
    "R Ashwin": "AR",
    "Mohammed Shami": "BOWL",
    "B Kumar": "BOWL",
    "Arshdeep Singh": "BOWL",
}

PLAYER_CREDITS: Dict[str, float] = {
    "V Kohli": 9.5,
    "Babar Azam": 9.0,
    "Mohammad Rizwan": 9.0,
    "HH Pandya": 9.0,
    "RG Sharma": 8.5,
    "SA Yadav": 9.0,
    "Shaheen Shah Afridi": 8.5,
    "Haris Rauf": 8.5,
    "Arshdeep Singh": 8.5,
    "Shadab Khan": 8.5,
    "KL Rahul": 8.5,
    "Shan Masood": 8.0,
    "Iftikhar Ahmed": 8.0,
    "Mohammed Shami": 8.5,
    "B Kumar": 8.0,
    "Mohammad Nawaz": 8.0,
    "R Ashwin": 7.5,
    "KD Karthik": 7.5,
    "Naseem Shah": 7.5,
    "AR Patel": 8.0,
    "Haider Ali": 7.5,
    "Asif Ali": 7.5,
}

class MatchService:
    def __init__(self, json_path: str):
        self.json_path = json_path
        self._load_data()

    def _load_data(self):
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.raw_data = json.load(f)

        info = self.raw_data.get("info", {})
        self.teams: List[str] = info.get("teams", [])
        self.event_name = info.get("event", {}).get("name", "T20 Match")
        self.venue = info.get("venue", "Cricket Ground")
        self.city = info.get("city", "")
        self.dates = info.get("dates", [])
        self.toss = info.get("toss", {})
        self.outcome = info.get("outcome", {})
        self.raw_players = info.get("players", {})

        self.deliveries: List[Delivery] = []
        self._flatten_deliveries()

    def _flatten_deliveries(self):
        innings_list = self.raw_data.get("innings", [])
        current_idx = 0

        for inn_idx, inn in enumerate(innings_list):
            innings_num = inn_idx + 1
            team_batting = inn.get("team", "")
            team_bowling = self.teams[1] if team_batting == self.teams[0] else self.teams[0]

            for over_obj in inn.get("overs", []):
                over_num = over_obj.get("over", 0)
                over_deliveries = over_obj.get("deliveries", [])
                
                # Check maiden status for this over:
                # 1. Count legal deliveries (excluding wides and no-balls).
                # 2. Exclude runs not charged to bowler (byes and leg-byes).
                # 3. A maiden over requires a completed qualifying over (at least 6 legal deliveries).
                legal_balls_in_over = 0
                bowler_runs_in_over = 0
                for dlv in over_deliveries:
                    b_runs = dlv.get("runs", {}).get("batter", 0)
                    extras = dlv.get("extras", {})
                    e_bowler = extras.get("wides", 0) + extras.get("noballs", 0)
                    bowler_runs_in_over += (b_runs + e_bowler)
                    if "wides" not in extras and "noballs" not in extras:
                        legal_balls_in_over += 1

                is_maiden_over = (legal_balls_in_over >= 6 and bowler_runs_in_over == 0)

                for b_idx, dlv in enumerate(over_deliveries):
                    batter = dlv.get("batter", "")
                    bowler = dlv.get("bowler", "")
                    non_striker = dlv.get("non_striker", "")
                    runs_obj = dlv.get("runs", {})
                    batter_runs = runs_obj.get("batter", 0)
                    extra_runs = runs_obj.get("extras", 0)
                    total_runs = runs_obj.get("total", 0)
                    non_boundary = bool(runs_obj.get("non_boundary", False))

                    extras_obj = dlv.get("extras", {})
                    extra_type = list(extras_obj.keys())[0] if extras_obj else None

                    wickets_list = dlv.get("wickets", [])
                    is_wicket = len(wickets_list) > 0
                    parsed_wickets: List[WicketDetail] = []
                    all_fielders: List[str] = []
                    all_players_out: List[str] = []

                    for w_info in wickets_list:
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

                    # Direct hit verification: default to None (unverified) unless explicitly stated
                    direct_hit = None
                    if is_wicket and any(w.kind == "run out" for w in parsed_wickets):
                        for w_info in wickets_list:
                            if "direct_hit" in w_info:
                                direct_hit = bool(w_info["direct_hit"])
                                break
                            elif "directhit" in w_info:
                                direct_hit = bool(w_info["directhit"])
                                break

                    # Genuine boundaries: non_boundary 4s/6s (e.g. overthrows/running)
                    # award batter run points, but do NOT award boundary bonus points.
                    is_four = (batter_runs == 4 and extra_type is None and not non_boundary)
                    is_six = (batter_runs == 6 and extra_type is None and not non_boundary)
                    is_dot = (total_runs == 0 and not is_wicket)
                    
                    is_maiden_completing = (
                        is_maiden_over and (b_idx == len(over_deliveries) - 1)
                    )

                    over_display = f"{over_num}.{b_idx + 1}"
                    
                    summary = self._create_summary(
                        batter, bowler, batter_runs, extra_runs, extra_type,
                        is_wicket, wicket_kind, player_out, all_fielders,
                        non_boundary=non_boundary,
                        parsed_wickets=parsed_wickets
                    )

                    delivery = Delivery(
                        index=current_idx,
                        innings=innings_num,
                        team_batting=team_batting,
                        team_bowling=team_bowling,
                        over=over_num,
                        ball_in_over=b_idx + 1,
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
                        is_maiden_completing_ball=is_maiden_completing,
                        summary=summary
                    )
                    self.deliveries.append(delivery)
                    current_idx += 1

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
                return f"WICKET! {bowler} to {player_out}, {w_kind.upper()}! Clean breakthrough."
            elif w_kind == "run out":
                f_name = " & ".join(fielders) if fielders else "fielders"
                return f"RUN OUT! {player_out} run out by {f_name}."
            else:
                return f"WICKET! {player_out} dismissed ({w_kind}) off {bowler}."
        
        if e_type:
            return f"{bowler} to {batter}, {e_runs} EXTRA ({e_type.upper()})."
        if b_runs == 6:
            if non_boundary:
                return f"{bowler} to {batter}, 6 runs taken (all-run / overthrows, non-boundary)."
            return f"MAXIMUM! {bowler} to {batter}, SIX runs launched over the boundary!"
        if b_runs == 4:
            if non_boundary:
                return f"{bowler} to {batter}, 4 runs taken (all-run / overthrows, non-boundary)."
            return f"FOUR! {bowler} to {batter}, cracked through the gap to the fence!"
        if b_runs == 0:
            return f"{bowler} to {batter}, no run. Solid defensive play."
        return f"{bowler} to {batter}, {b_runs} run{'s' if b_runs > 1 else ''} taken."

    def get_metadata(self) -> MatchMetadata:
        roster_list: List[PlayerInfo] = []
        for team, plist in self.raw_players.items():
            for p in plist:
                roster_list.append(PlayerInfo(
                    name=p,
                    team=team,
                    role=PLAYER_ROLES.get(p, "BAT"),
                    credits=PLAYER_CREDITS.get(p, 8.5)
                ))

        return MatchMetadata(
            match_id="1298150",
            event_name=self.event_name,
            venue=self.venue,
            city=self.city,
            dates=self.dates,
            teams=self.teams,
            toss=self.toss,
            outcome=self.outcome,
            total_deliveries=len(self.deliveries),
            players=self.raw_players,
            roster=roster_list,
            source_attribution="Data provided by Cricsheet (https://cricsheet.org), licensed under Open Data Commons Attribution License (ODC-BY 1.0)."
        )

    def get_delivery(self, index: int) -> Optional[Delivery]:
        if 0 <= index < len(self.deliveries):
            return self.deliveries[index]
        return None

    def get_scoreboard_at(self, ball_index: int) -> ScoreboardState:
        if not self.deliveries:
            raise ValueError("No deliveries available")

        clamped_idx = max(0, min(ball_index, len(self.deliveries) - 1))
        target_delivery = self.deliveries[clamped_idx]
        current_innings = target_delivery.innings

        # Innings 1 totals
        inn1_runs = 0
        inn1_wickets = 0

        # Current innings tracking
        team_score = 0
        team_wickets = 0
        legal_balls = 0

        batters: Dict[str, Dict[str, Any]] = {}
        bowlers: Dict[str, Dict[str, Any]] = {}

        # Recent balls in current innings
        recent_balls: List[Dict[str, Any]] = []

        for i in range(clamped_idx + 1):
            dlv = self.deliveries[i]
            if dlv.innings == 1:
                inn1_runs += dlv.total_runs
                if dlv.is_wicket:
                    inn1_wickets += 1

            if dlv.innings == current_innings:
                team_score += dlv.total_runs
                if dlv.is_wicket:
                    team_wickets += 1
                
                # Check legal ball (not wide and not no-ball in standard cricket count)
                is_legal = dlv.extra_type not in ("wides", "noballs")
                if is_legal:
                    legal_balls += 1

                # Update batter
                b_name = dlv.batter
                if b_name not in batters:
                    batters[b_name] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None}
                
                batters[b_name]["runs"] += dlv.batter_runs
                if dlv.extra_type != "wides":
                    batters[b_name]["balls"] += 1
                if dlv.is_four:
                    batters[b_name]["fours"] += 1
                if dlv.is_six:
                    batters[b_name]["sixes"] += 1

                if dlv.is_wicket and dlv.player_out:
                    p_out = dlv.player_out
                    if p_out not in batters:
                        batters[p_out] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None}
                    batters[p_out]["is_out"] = True
                    batters[p_out]["dismissal"] = dlv.wicket_kind

                # Update bowler
                bw_name = dlv.bowler
                if bw_name not in bowlers:
                    bowlers[bw_name] = {"legal_balls": 0, "runs_conceded": 0, "wickets": 0, "maidens": 0}
                
                # Conceded runs by bowler
                bowler_extras = dlv.extra_runs if dlv.extra_type in ("wides", "noballs") else 0
                bowlers[bw_name]["runs_conceded"] += (dlv.batter_runs + bowler_extras)
                
                if is_legal:
                    bowlers[bw_name]["legal_balls"] += 1

                if dlv.is_wicket and dlv.wicket_kind not in ("run out", "retired hurt"):
                    bowlers[bw_name]["wickets"] += 1

                if dlv.is_maiden_completing_ball:
                    bowlers[bw_name]["maidens"] += 1

                recent_balls.append({
                    "index": dlv.index,
                    "over_display": dlv.over_display,
                    "total_runs": dlv.total_runs,
                    "is_wicket": dlv.is_wicket,
                    "is_four": dlv.is_four,
                    "is_six": dlv.is_six,
                    "extra_type": dlv.extra_type
                })

        # Calculate overs display
        completed_overs = legal_balls // 6
        rem_balls = legal_balls % 6
        overs_display = f"{completed_overs}.{rem_balls}"

        # Current Run Rate
        overs_float = completed_overs + (rem_balls / 6.0)
        crr = round(team_score / overs_float, 2) if overs_float > 0 else 0.0

        # Target & Required Run Rate (for Innings 2)
        target = (inn1_runs + 1) if current_innings == 2 else None
        required_rr = None
        runs_needed = None
        balls_remaining = None

        if current_innings == 2 and target is not None:
            runs_needed = max(0, target - team_score)
            balls_remaining = max(0, 120 - legal_balls)
            if balls_remaining > 0 and runs_needed > 0:
                required_rr = round((runs_needed / balls_remaining) * 6.0, 2)
            elif runs_needed == 0:
                required_rr = 0.0

        # Striker stats
        striker_name = target_delivery.batter
        s_data = batters.get(striker_name, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None})
        s_sr = round((s_data["runs"] / s_data["balls"]) * 100, 1) if s_data["balls"] > 0 else 0.0
        striker_stats = BatterLiveStats(
            name=striker_name,
            runs=s_data["runs"],
            balls=s_data["balls"],
            fours=s_data["fours"],
            sixes=s_data["sixes"],
            strike_rate=s_sr,
            is_out=s_data["is_out"],
            dismissal_desc=s_data["dismissal"]
        )

        # Non-striker stats
        non_striker_name = target_delivery.non_striker
        ns_data = batters.get(non_striker_name, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "is_out": False, "dismissal": None})
        ns_sr = round((ns_data["runs"] / ns_data["balls"]) * 100, 1) if ns_data["balls"] > 0 else 0.0
        non_striker_stats = BatterLiveStats(
            name=non_striker_name,
            runs=ns_data["runs"],
            balls=ns_data["balls"],
            fours=ns_data["fours"],
            sixes=ns_data["sixes"],
            strike_rate=ns_sr,
            is_out=ns_data["is_out"],
            dismissal_desc=ns_data["dismissal"]
        )

        # Bowler stats
        bowler_name = target_delivery.bowler
        bw_data = bowlers.get(bowler_name, {"legal_balls": 0, "runs_conceded": 0, "wickets": 0, "maidens": 0})
        bw_overs_comp = bw_data["legal_balls"] // 6
        bw_rem = bw_data["legal_balls"] % 6
        bw_overs_display = bw_overs_comp + (bw_rem / 10.0)
        bw_overs_float = bw_overs_comp + (bw_rem / 6.0)
        bw_econ = round(bw_data["runs_conceded"] / bw_overs_float, 2) if bw_overs_float > 0 else 0.0

        bowler_stats = BowlerLiveStats(
            name=bowler_name,
            overs=bw_overs_display,
            legal_balls=bw_data["legal_balls"],
            maidens=bw_data["maidens"],
            runs_conceded=bw_data["runs_conceded"],
            wickets=bw_data["wickets"],
            economy=bw_econ
        )

        # Determine status string
        if clamped_idx == len(self.deliveries) - 1:
            match_status = "Match Completed: India won by 4 wickets"
        elif current_innings == 1:
            match_status = f"1st Innings: {target_delivery.team_batting} batting"
        else:
            if runs_needed is not None and runs_needed > 0:
                match_status = f"{target_delivery.team_batting} need {runs_needed} runs from {balls_remaining} balls"
            else:
                match_status = "Target Achieved!"

        return ScoreboardState(
            ball_index=clamped_idx,
            innings=current_innings,
            batting_team=target_delivery.team_batting,
            bowling_team=target_delivery.team_bowling,
            team_score=team_score,
            team_wickets=team_wickets,
            overs_display=overs_display,
            legal_balls_bowled=legal_balls,
            run_rate=crr,
            target=target,
            required_run_rate=required_rr,
            runs_needed=runs_needed,
            balls_remaining=balls_remaining,
            striker=striker_stats,
            non_striker=non_striker_stats,
            bowler=bowler_stats,
            recent_balls=recent_balls[-12:],
            match_status=match_status
        )

