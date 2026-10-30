from typing import Dict, List, Optional, Any, Set
from app.models.match import Delivery, MatchMetadata, WicketDetail
from app.models.fantasy import (
    PlayerFantasyScore, BreakdownItem,
    PlayerDelta, BallFantasyImpact, FantasyTeamConfig
)
from app.scoring.ruleset import RulesetConfig, DEFAULT_RULESET
from app.services.match_service import PLAYER_ROLES

class FantasyEngine:
    def __init__(self, deliveries: List[Delivery], metadata: MatchMetadata, ruleset: Optional[RulesetConfig] = None):
        self.deliveries = deliveries
        self.metadata = metadata
        self.ruleset = ruleset or DEFAULT_RULESET
        
        # All 22 players get starting XI bonus
        self.all_players: Set[str] = set()
        for t, plist in metadata.players.items():
            for p in plist:
                self.all_players.add(p)

        # Ensure maiden over completions are tagged if deliveries were passed untagged
        if self.deliveries and not any(d.is_maiden_completing_ball for d in self.deliveries):
            self._tag_maiden_deliveries()

    def _tag_maiden_deliveries(self):
        """
        Scans deliveries grouped by (innings, over) to tag the final delivery of completed maiden overs.
        A qualifying maiden requires:
        1. At least 6 legal deliveries (excluding wides and no-balls).
        2. 0 runs conceded by bowler (batter runs + wides + no-balls == 0; byes/legbyes excluded).
        3. Bowled by a single bowler.
        """
        from collections import defaultdict
        overs_map = defaultdict(list)
        for d in self.deliveries:
            overs_map[(d.innings, d.over)].append(d)

        for (inn, ov), ov_dlvs in overs_map.items():
            legal_balls = 0
            bowler_runs = 0
            bowlers = set()
            for d in ov_dlvs:
                bowlers.add(d.bowler)
                bowler_extras = d.extra_runs if d.extra_type in ("wides", "noballs") else 0
                bowler_runs += (d.batter_runs + bowler_extras)
                if d.extra_type not in ("wides", "noballs"):
                    legal_balls += 1

            if legal_balls >= 6 and bowler_runs == 0 and len(bowlers) == 1:
                # Last delivery of completed maiden over
                ov_dlvs[-1].is_maiden_completing_ball = True

    def calculate_player_points_at(
        self,
        player_name: str,
        ball_index: int,
        is_captain: bool = False,
        is_vice_captain: bool = False
    ) -> PlayerFantasyScore:
        role = PLAYER_ROLES.get(player_name, "BAT")
        team = ""
        for t, plist in self.metadata.players.items():
            if player_name in plist:
                team = t
                break

        multiplier = 1.0
        if is_captain:
            multiplier = self.ruleset.captain_multiplier
        elif is_vice_captain:
            multiplier = self.ruleset.vice_captain_multiplier

        breakdown: List[BreakdownItem] = []

        # 1. Starting XI Bonus (+4 pts)
        if player_name in self.all_players:
            breakdown.append(BreakdownItem(
                category="general",
                label="Starting XI Announced",
                count=1,
                points_each=self.ruleset.starting_xi,
                total_points=self.ruleset.starting_xi
            ))

        if not self.deliveries:
            raw_sum = sum(item.total_points for item in breakdown)
            total_pts = raw_sum * multiplier
            return PlayerFantasyScore(
                player_name=player_name,
                team=team,
                role=role,
                is_captain=is_captain,
                is_vice_captain=is_vice_captain,
                multiplier=multiplier,
                raw_points=round(raw_sum, 1),
                total_points=round(total_pts, 1),
                breakdown=breakdown,
                recent_delta=0.0
            )

        # Tally stats up to ball_index
        clamped_idx = max(0, min(ball_index, len(self.deliveries) - 1))
        
        # Batting stats
        runs_scored = 0
        balls_faced = 0
        fours_hit = 0
        sixes_hit = 0
        is_dismissed = False
        dismissal_kind = None

        # Bowling stats
        legal_balls_bowled = 0
        runs_conceded = 0
        wickets_taken = 0
        lbw_bowled_count = 0
        maidens_count = 0
        dot_balls_count = 0

        # Fielding stats
        catches_taken = 0
        stumpings_made = 0
        run_outs_direct = 0
        run_outs_shared = 0

        for i in range(clamped_idx + 1):
            dlv = self.deliveries[i]
            is_legal = dlv.extra_type not in ("wides", "noballs")
            bowler_extras = dlv.extra_runs if dlv.extra_type in ("wides", "noballs") else 0

            # Batting
            if dlv.batter == player_name:
                runs_scored += dlv.batter_runs
                if dlv.extra_type != "wides":
                    balls_faced += 1
                if dlv.is_four:
                    fours_hit += 1
                if dlv.is_six:
                    sixes_hit += 1

            active_wickets: List[WicketDetail] = dlv.wickets if dlv.wickets else (
                [WicketDetail(kind=dlv.wicket_kind or "", player_out=dlv.player_out or "", fielders=dlv.fielders)]
                if dlv.is_wicket else []
            )

            if dlv.is_wicket:
                for w_item in active_wickets:
                    if w_item.player_out == player_name:
                        is_dismissed = True
                        dismissal_kind = w_item.kind

            # Bowling
            if dlv.bowler == player_name:
                runs_conceded += (dlv.batter_runs + bowler_extras)

                if is_legal:
                    legal_balls_bowled += 1
                    if (dlv.batter_runs + bowler_extras) == 0:
                        dot_balls_count += 1

                if dlv.is_wicket:
                    for w_item in active_wickets:
                        if w_item.kind not in ("run out", "retired hurt"):
                            wickets_taken += 1
                            if w_item.kind in ("bowled", "lbw"):
                                lbw_bowled_count += 1

                if dlv.is_maiden_completing_ball:
                    maidens_count += 1

            # Fielding
            if dlv.is_wicket:
                for w_item in active_wickets:
                    if player_name in w_item.fielders:
                        if w_item.kind == "caught":
                            catches_taken += 1
                        elif w_item.kind == "stumped":
                            stumpings_made += 1
                        elif w_item.kind == "run out":
                            if dlv.direct_hit is True:
                                run_outs_direct += 1
                            else:
                                run_outs_shared += 1

        # --- Evaluate Batting Points ---
        if runs_scored > 0:
            breakdown.append(BreakdownItem(
                category="batting",
                label=f"Runs Scored ({runs_scored})",
                count=runs_scored,
                points_each=self.ruleset.run,
                total_points=runs_scored * self.ruleset.run
            ))

        if fours_hit > 0:
            breakdown.append(BreakdownItem(
                category="batting",
                label=f"Boundary 4s ({fours_hit})",
                count=fours_hit,
                points_each=self.ruleset.boundary_four_bonus,
                total_points=fours_hit * self.ruleset.boundary_four_bonus
            ))

        if sixes_hit > 0:
            breakdown.append(BreakdownItem(
                category="batting",
                label=f"Boundary 6s ({sixes_hit})",
                count=sixes_hit,
                points_each=self.ruleset.six_bonus,
                total_points=sixes_hit * self.ruleset.six_bonus
            ))

        # Batting Milestones: Century (16) > 75 (12) > 50 (8) > 25 (4) non-stacking
        if runs_scored >= 100:
            breakdown.append(BreakdownItem(
                category="batting",
                label="Century Bonus (100+)",
                count=1,
                points_each=self.ruleset.century_bonus,
                total_points=self.ruleset.century_bonus
            ))
        elif runs_scored >= 75:
            breakdown.append(BreakdownItem(
                category="batting",
                label="75-Run Milestone Bonus",
                count=1,
                points_each=self.ruleset.seventy_five_run_bonus,
                total_points=self.ruleset.seventy_five_run_bonus
            ))
        elif runs_scored >= 50:
            breakdown.append(BreakdownItem(
                category="batting",
                label="Half-Century Bonus (50+)",
                count=1,
                points_each=self.ruleset.half_century_bonus,
                total_points=self.ruleset.half_century_bonus
            ))
        elif runs_scored >= 25:
            breakdown.append(BreakdownItem(
                category="batting",
                label="25-Run Milestone Bonus",
                count=1,
                points_each=self.ruleset.twenty_five_run_bonus,
                total_points=self.ruleset.twenty_five_run_bonus
            ))

        # Duck penalty (applies to BAT, WK, AR if dismissed for 0)
        if is_dismissed and runs_scored == 0 and role in ("BAT", "WK", "AR"):
            breakdown.append(BreakdownItem(
                category="batting",
                label="Dismissal for Duck",
                count=1,
                points_each=self.ruleset.duck_penalty,
                total_points=self.ruleset.duck_penalty
            ))

        # Strike Rate Bonus/Penalty (min 10 balls faced; not applicable for BOWL)
        if balls_faced >= self.ruleset.strike_rate.min_balls and role != "BOWL":
            sr = (runs_scored / balls_faced) * 100.0
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

        # --- Evaluate Bowling Points ---
        if wickets_taken > 0:
            breakdown.append(BreakdownItem(
                category="bowling",
                label=f"Wickets Taken ({wickets_taken})",
                count=wickets_taken,
                points_each=self.ruleset.wicket_normal,
                total_points=wickets_taken * self.ruleset.wicket_normal
            ))

        if lbw_bowled_count > 0:
            breakdown.append(BreakdownItem(
                category="bowling",
                label=f"Bowled / LBW Bonus ({lbw_bowled_count})",
                count=lbw_bowled_count,
                points_each=self.ruleset.lbw_bowled_bonus,
                total_points=lbw_bowled_count * self.ruleset.lbw_bowled_bonus
            ))

        if dot_balls_count > 0:
            breakdown.append(BreakdownItem(
                category="bowling",
                label=f"Dot Balls Bowled ({dot_balls_count})",
                count=dot_balls_count,
                points_each=self.ruleset.dot_ball_bowled,
                total_points=dot_balls_count * self.ruleset.dot_ball_bowled
            ))

        # Wicket milestone bonuses: 5W [12] > 4W [8] > 3W [4] non-stacking
        if wickets_taken >= 5:
            breakdown.append(BreakdownItem(
                category="bowling",
                label="5-Wicket Haul Bonus",
                count=1,
                points_each=self.ruleset.five_wicket_bonus,
                total_points=self.ruleset.five_wicket_bonus
            ))
        elif wickets_taken == 4:
            breakdown.append(BreakdownItem(
                category="bowling",
                label="4-Wicket Haul Bonus",
                count=1,
                points_each=self.ruleset.four_wicket_bonus,
                total_points=self.ruleset.four_wicket_bonus
            ))
        elif wickets_taken == 3:
            breakdown.append(BreakdownItem(
                category="bowling",
                label="3-Wicket Haul Bonus",
                count=1,
                points_each=self.ruleset.three_wicket_bonus,
                total_points=self.ruleset.three_wicket_bonus
            ))

        if maidens_count > 0:
            breakdown.append(BreakdownItem(
                category="bowling",
                label=f"Maiden Overs ({maidens_count})",
                count=maidens_count,
                points_each=self.ruleset.maiden_over,
                total_points=maidens_count * self.ruleset.maiden_over
            ))

        # Economy rate bonus/penalty (min 2 overs = 12 legal balls)
        if legal_balls_bowled >= self.ruleset.economy_rate.min_legal_balls:
            overs_float = legal_balls_bowled / 6.0
            econ = runs_conceded / overs_float
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

        # --- Evaluate Fielding Points ---
        if catches_taken > 0:
            breakdown.append(BreakdownItem(
                category="fielding",
                label=f"Catches ({catches_taken})",
                count=catches_taken,
                points_each=self.ruleset.catch,
                total_points=catches_taken * self.ruleset.catch
            ))
            if catches_taken >= 3:
                breakdown.append(BreakdownItem(
                    category="fielding",
                    label="3 Catch Bonus",
                    count=1,
                    points_each=self.ruleset.three_catch_bonus,
                    total_points=self.ruleset.three_catch_bonus
                ))

        if stumpings_made > 0:
            breakdown.append(BreakdownItem(
                category="fielding",
                label=f"Stumpings ({stumpings_made})",
                count=stumpings_made,
                points_each=self.ruleset.stumping,
                total_points=stumpings_made * self.ruleset.stumping
            ))

        if run_outs_direct > 0:
            breakdown.append(BreakdownItem(
                category="fielding",
                label=f"Direct Run Outs ({run_outs_direct})",
                count=run_outs_direct,
                points_each=self.ruleset.run_out_direct,
                total_points=run_outs_direct * self.ruleset.run_out_direct
            ))

        if run_outs_shared > 0:
            breakdown.append(BreakdownItem(
                category="fielding",
                label=f"Run Outs ({run_outs_shared})",
                count=run_outs_shared,
                points_each=self.ruleset.run_out_shared,
                total_points=run_outs_shared * self.ruleset.run_out_shared
            ))

        raw_sum = sum(item.total_points for item in breakdown)
        total_pts = raw_sum * multiplier

        return PlayerFantasyScore(
            player_name=player_name,
            team=team,
            role=role,
            is_captain=is_captain,
            is_vice_captain=is_vice_captain,
            multiplier=multiplier,
            raw_points=round(raw_sum, 1),
            total_points=round(total_pts, 1),
            breakdown=breakdown,
            recent_delta=0.0
        )

    def get_all_player_scores_at(
        self,
        ball_index: int,
        fantasy_team: Optional[FantasyTeamConfig] = None
    ) -> Dict[str, PlayerFantasyScore]:
        scores: Dict[str, PlayerFantasyScore] = {}
        c_name = fantasy_team.captain if fantasy_team else ""
        vc_name = fantasy_team.vice_captain if fantasy_team else ""

        for player_name in self.all_players:
            is_c = (player_name == c_name)
            is_vc = (player_name == vc_name)
            score = self.calculate_player_points_at(
                player_name=player_name,
                ball_index=ball_index,
                is_captain=is_c,
                is_vice_captain=is_vc
            )
            scores[player_name] = score

        return scores

    def calculate_ball_delta(
        self,
        ball_index: int,
        fantasy_team: Optional[FantasyTeamConfig] = None
    ) -> BallFantasyImpact:
        if not self.deliveries:
            return BallFantasyImpact(
                delivery_index=0,
                over_display="0.0",
                player_deltas=[],
                fantasy_team_total=0.0,
                fantasy_team_delta=0.0,
                summary_sentence="No match data loaded"
            )

        clamped_idx = max(0, min(ball_index, len(self.deliveries) - 1))
        target_delivery = self.deliveries[clamped_idx]
        is_legal = target_delivery.extra_type not in ("wides", "noballs")
        bowler_extras = target_delivery.extra_runs if target_delivery.extra_type in ("wides", "noballs") else 0

        # Calculate scores at ball_index and at ball_index - 1
        current_scores = self.get_all_player_scores_at(clamped_idx, fantasy_team)
        prev_scores = (
            self.get_all_player_scores_at(clamped_idx - 1, fantasy_team)
            if clamped_idx > 0
            else {}
        )

        selected_set = set(fantasy_team.selected_players) if fantasy_team else set()
        c_name = fantasy_team.captain if fantasy_team else ""
        vc_name = fantasy_team.vice_captain if fantasy_team else ""

        player_deltas: List[PlayerDelta] = []
        fantasy_team_delta = 0.0
        fantasy_team_total = 0.0

        for p in selected_set:
            if p in current_scores:
                fantasy_team_total += current_scores[p].total_points

        for player_name, cur_score in current_scores.items():
            prev_total = prev_scores[player_name].total_points if player_name in prev_scores else self.ruleset.starting_xi * cur_score.multiplier
            diff = round(cur_score.total_points - prev_total, 1)

            if abs(diff) > 0.001:
                reasons = []
                category = "general"
                is_c = (player_name == c_name)
                is_vc = (player_name == vc_name)

                if player_name == target_delivery.batter:
                    category = "batting"
                    if target_delivery.batter_runs > 0:
                        reasons.append(f"+{target_delivery.batter_runs} run(s)")
                    if target_delivery.is_four:
                        reasons.append(f"Boundary 4 bonus (+{self.ruleset.boundary_four_bonus:.0f})")
                    if target_delivery.is_six:
                        reasons.append(f"Boundary 6 bonus (+{self.ruleset.six_bonus:.0f})")

                active_wickets: List[WicketDetail] = target_delivery.wickets if target_delivery.wickets else (
                    [WicketDetail(kind=target_delivery.wicket_kind or "", player_out=target_delivery.player_out or "", fielders=target_delivery.fielders)]
                    if target_delivery.is_wicket else []
                )

                if player_name == target_delivery.bowler:
                    category = "bowling"
                    if is_legal and (target_delivery.batter_runs + bowler_extras) == 0:
                        reasons.append(f"Dot ball bowled (+{self.ruleset.dot_ball_bowled:.0f})")
                    if target_delivery.is_wicket:
                        for w_item in active_wickets:
                            if w_item.kind not in ("run out", "retired hurt"):
                                reasons.append(f"Wicket taken (+{self.ruleset.wicket_normal:.0f})")
                                if w_item.kind in ("bowled", "lbw"):
                                    reasons.append(f"Bowled/LBW bonus (+{self.ruleset.lbw_bowled_bonus:.0f})")

                if target_delivery.is_wicket:
                    for w_item in active_wickets:
                        if player_name in w_item.fielders:
                            category = "fielding"
                            if w_item.kind == "caught":
                                reasons.append(f"Catch (+{self.ruleset.catch:.0f})")
                            elif w_item.kind == "stumped":
                                reasons.append(f"Stumping (+{self.ruleset.stumping:.0f})")
                            elif w_item.kind == "run out":
                                if target_delivery.direct_hit is True:
                                    reasons.append(f"Direct hit run out (+{self.ruleset.run_out_direct:.0f})")
                                else:
                                    reasons.append(f"Run out (+{self.ruleset.run_out_shared:.0f}, direct-hit unverified)")

                if target_delivery.is_wicket and any(player_name == w_item.player_out for w_item in active_wickets):
                    category = "batting"
                    reasons.append("Batter Dismissed")

                reason_text = ", ".join(reasons) if reasons else "Match event point adjustment"
                raw_diff = round(diff / cur_score.multiplier, 1)

                player_delta = PlayerDelta(
                    player_name=player_name,
                    team=cur_score.team,
                    reason=reason_text,
                    category=category,
                    raw_delta=raw_diff,
                    multiplier=cur_score.multiplier,
                    net_delta=diff,
                    previous_total=round(prev_total, 1),
                    new_total=cur_score.total_points,
                    is_captain=is_c,
                    is_vice_captain=is_vc
                )
                player_deltas.append(player_delta)

                if player_name in selected_set:
                    fantasy_team_delta += diff

        if player_deltas:
            delta_strs = [
                f"{d.player_name} ({'+' if d.net_delta > 0 else ''}{d.net_delta} pts{' [C]' if d.is_captain else ' [VC]' if d.is_vice_captain else ''})"
                for d in player_deltas
            ]
            summary_sentence = f"Ball {target_delivery.over_display}: " + "; ".join(delta_strs) + f". Team Impact: {'+' if fantasy_team_delta >= 0 else ''}{round(fantasy_team_delta, 1)} pts."
        else:
            summary_sentence = f"Ball {target_delivery.over_display}: No fantasy points earned on this delivery."

        return BallFantasyImpact(
            delivery_index=clamped_idx,
            over_display=target_delivery.over_display,
            player_deltas=player_deltas,
            fantasy_team_total=round(fantasy_team_total, 1),
            fantasy_team_delta=round(fantasy_team_delta, 1),
            summary_sentence=summary_sentence
        )
