import os
import json
from typing import Optional, Dict, Any, List
from app.models.match import Delivery, ScoreboardState
from app.models.fantasy import BallFantasyImpact
from app.models.explanation import (
    EventExplanation, RuleExplanation, EvidenceBoundary
)

CRICKET_LAWS: Dict[str, Dict[str, str]] = {
    "bowled": {
        "law_name": "Bowled",
        "law_number": "MCC Law 32",
        "summary": "The striker is out Bowled if his wicket is put down by a ball delivered by the bowler, not being a No ball. Directly penetrates the batter's defense and hits the stumps."
    },
    "caught": {
        "law_name": "Caught",
        "law_number": "MCC Law 33",
        "summary": "The striker is out Caught if a ball delivered by the bowler touches his bat without having previously touched any umpire or fielder, and is subsequently held by a fielder as a fair catch before it touches the ground."
    },
    "lbw": {
        "law_name": "Leg Before Wicket (LBW)",
        "law_number": "MCC Law 36",
        "summary": "The striker is out LBW if the ball delivered by the bowler pitches in line or outside off-stump, is not hit with the bat, and strikes the person of the batter intercepting a trajectory that would have hit the stumps."
    },
    "run out": {
        "law_name": "Run Out",
        "law_number": "MCC Law 38",
        "summary": "Either batter is out Run Out if, at any time while the ball is in play, he is out of his ground and his wicket is fairly broken by action of a fielder."
    },
    "stumped": {
        "law_name": "Stumped",
        "law_number": "MCC Law 39",
        "summary": "The striker is out Stumped if a ball delivered by the bowler is not a No ball, he is out of his ground receiving the ball, does not attempt a run, and the wicket-keeper fairly puts the wicket down."
    },
    "four": {
        "law_name": "Boundary Four",
        "law_number": "MCC Law 19",
        "summary": "A boundary four is scored when the ball makes contact with or crosses the boundary rope having touched the ground within the field of play."
    },
    "six": {
        "law_name": "Boundary Six (Maximum)",
        "law_number": "MCC Law 19",
        "summary": "A boundary six is scored when a ball struck by the batter crosses or lands beyond the boundary rope on the full without touching the ground."
    },
    "wides": {
        "law_name": "Wide Ball",
        "law_number": "MCC Law 22",
        "summary": "A delivery judged by the umpire to have passed too far from the striker to be reached by him with the bat from a normal batting stroke. 1 extra run awarded and must be rebowled."
    },
    "noballs": {
        "law_name": "No Ball",
        "law_number": "MCC Law 21",
        "summary": "An illegal delivery due to bowler foot-fault over the popping crease or dangerous height. 1 penalty run awarded to the batting team, plus a Free Hit on the subsequent delivery in T20 cricket."
    },
    "dot": {
        "law_name": "Dot Ball / Defense",
        "law_number": "MCC Law 18",
        "summary": "A legal delivery on which no runs are scored off the bat or conceded through extras. Key building block of bowling pressure."
    },
    "standard_run": {
        "law_name": "Scoring Runs",
        "law_number": "MCC Law 18",
        "summary": "Runs are scored by batters running between their wickets following a stroke, or through overthrows and boundaries."
    }
}

class ExplanationService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def generate_explanation(
        self,
        delivery: Delivery,
        scoreboard: ScoreboardState,
        fantasy_impact: BallFantasyImpact
    ) -> EventExplanation:
        # If API key is present, attempt Gemini AI explanation
        if self.api_key:
            try:
                ai_exp = self._call_gemini_api(delivery, scoreboard, fantasy_impact)
                if ai_exp:
                    return ai_exp
            except Exception as e:
                # Log and smoothly fall back to deterministic engine
                print(f"[ExplanationService] Gemini API call failed: {e}. Falling back to deterministic rules engine.")

        # Deterministic rules-based explanation
        return self._generate_deterministic_explanation(delivery, scoreboard, fantasy_impact)

    def _generate_deterministic_explanation(
        self,
        delivery: Delivery,
        scoreboard: ScoreboardState,
        fantasy_impact: BallFantasyImpact
    ) -> EventExplanation:
        # Determine Cricket Law
        law_info = CRICKET_LAWS["standard_run"]
        if delivery.is_wicket:
            w_kind = delivery.wicket_kind or "caught"
            law_info = CRICKET_LAWS.get(w_kind, CRICKET_LAWS["caught"])
        elif delivery.is_six:
            law_info = CRICKET_LAWS["six"]
        elif delivery.is_four:
            law_info = CRICKET_LAWS["four"]
        elif delivery.extra_type:
            law_info = CRICKET_LAWS.get(delivery.extra_type, CRICKET_LAWS["standard_run"])
        elif delivery.is_dot:
            law_info = CRICKET_LAWS["dot"]

        # Formulate 'what_happened'
        if delivery.is_wicket:
            if delivery.wicket_kind == "caught":
                fielder_txt = f", safely held by {delivery.fielders[0]}" if delivery.fielders else ""
                what_happened = f"{delivery.bowler} bowls to {delivery.player_out}; false stroke resulting in a catch{fielder_txt}."
            elif delivery.wicket_kind == "lbw":
                what_happened = f"{delivery.bowler} traps {delivery.player_out} right in front of the stumps. Umpire upholds the LBW appeal."
            elif delivery.wicket_kind == "bowled":
                what_happened = f"{delivery.bowler} completely breaches the defense of {delivery.player_out}, crashing into the stumps!"
            elif delivery.wicket_kind == "run out":
                f_txt = f" by {', '.join(delivery.fielders)}" if delivery.fielders else ""
                what_happened = f"Miscommunication between {delivery.batter} and {delivery.non_striker}! {delivery.player_out} is run out{f_txt}."
            else:
                what_happened = f"{delivery.player_out} is dismissed ({delivery.wicket_kind}) off the bowling of {delivery.bowler}."
        elif delivery.is_six:
            what_happened = f"{delivery.batter} launches {delivery.bowler} for a massive SIX over the ropes!"
        elif delivery.is_four:
            what_happened = f"{delivery.batter} finds the fence with a sublime boundary FOUR off {delivery.bowler}."
        elif delivery.extra_type:
            what_happened = f"{delivery.bowler} strays off line, conceding {delivery.extra_runs} extra run(s) as a {delivery.extra_type.upper()}."
        elif delivery.is_dot:
            what_happened = f"Dot ball! {delivery.bowler} delivers a disciplined ball to {delivery.batter}, beating the drive or kept to cover."
        else:
            what_happened = f"{delivery.batter} works {delivery.bowler} into the gap for {delivery.batter_runs} run{'s' if delivery.batter_runs > 1 else ''}."

        # Formulate 'why_it_matters'
        if delivery.innings == 2 and scoreboard.runs_needed is not None:
            if delivery.is_wicket:
                why_it_matters = f"Major breakthrough for {delivery.team_bowling}! The target of {scoreboard.target} now requires {scoreboard.runs_needed} runs from {scoreboard.balls_remaining} balls at {scoreboard.required_run_rate} RPO with {scoreboard.team_wickets} wickets down."
            elif delivery.is_six or delivery.is_four:
                why_it_matters = f"Pressure release for {delivery.team_batting}! Reduces target equation to {scoreboard.runs_needed} runs from {scoreboard.balls_remaining} balls (Req RR: {scoreboard.required_run_rate})."
            else:
                why_it_matters = f"Chase progression: {delivery.team_batting} currently at {scoreboard.team_score}/{scoreboard.team_wickets} after {scoreboard.overs_display} overs. Required rate sits at {scoreboard.required_run_rate}."
        else:
            if delivery.is_wicket:
                why_it_matters = f"Crucial setback for {delivery.team_batting} in 1st Innings. Stemming the flow of runs and exposing the middle order at {scoreboard.team_score}/{scoreboard.team_wickets}."
            elif delivery.is_six or delivery.is_four:
                why_it_matters = f"Run rate acceleration for {delivery.team_batting}, bringing current run rate to {scoreboard.run_rate} RPO."
            else:
                why_it_matters = f"1st innings scoreboard building: {delivery.team_batting} move to {scoreboard.team_score}/{scoreboard.team_wickets} in {scoreboard.overs_display} overs."

        # Evidence Boundaries
        grounded_facts = [
            f"Batter: {delivery.batter}, Bowler: {delivery.bowler}",
            f"Runs scored: {delivery.batter_runs} off bat, {delivery.extra_runs} extras (Total: {delivery.total_runs})"
        ]
        if delivery.is_wicket:
            grounded_facts.append(f"Official dismissal: {delivery.wicket_kind} (Player out: {delivery.player_out})")
            if delivery.fielders:
                grounded_facts.append(f"Fielding assist recorded: {', '.join(delivery.fielders)}")

        unavailable_evidence = [
            "Source dataset does not contain Hawk-Eye ball tracking trajectory or pitch map coordinates.",
            "Ultra-Edge / Snickometer audio frequency waveforms are not present in Cricsheet data.",
            "Delivery release speed (km/h) is unavailable in standard ball-by-ball record."
        ]

        if delivery.is_wicket and delivery.wicket_kind == "lbw":
            unavailable_evidence.append("DRS impact point (in line vs outside) and projected stumps hit cannot be verified from source records.")

        # Fantasy impact text
        if fantasy_impact.player_deltas:
            delta_lines = [
                f"{d.player_name}: {'+' if d.net_delta > 0 else ''}{d.net_delta} pts ({d.reason})"
                for d in fantasy_impact.player_deltas
            ]
            fantasy_impact_txt = f"Point shifts: " + "; ".join(delta_lines) + f". Net fantasy team shift: {'+' if fantasy_impact.fantasy_team_delta >= 0 else ''}{fantasy_impact.fantasy_team_delta} pts."
        else:
            fantasy_impact_txt = "No fantasy scoring criteria triggered on this delivery."

        fan_takeaway = f"{'Momentum shift!' if (delivery.is_wicket or delivery.is_six) else 'Tactical battle'} — {delivery.summary}"

        return EventExplanation(
            delivery_index=delivery.index,
            over_display=delivery.over_display,
            what_happened=what_happened,
            why_it_matters=why_it_matters,
            cricket_rule=RuleExplanation(
                law_name=law_info["law_name"],
                law_number=law_info["law_number"],
                summary=law_info["summary"]
            ),
            fantasy_impact=fantasy_impact_txt,
            evidence=EvidenceBoundary(
                grounded_in_data=grounded_facts,
                unavailable_evidence=unavailable_evidence
            ),
            fan_takeaway=fan_takeaway,
            engine_source="deterministic_rules_engine"
        )

    def _call_gemini_api(
        self,
        delivery: Delivery,
        scoreboard: ScoreboardState,
        fantasy_impact: BallFantasyImpact
    ) -> Optional[EventExplanation]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        prompt = f"""
You are the AI cricket explanation engine for BoundaryIQ.
Your task: Explain this specific cricket ball delivery to a fantasy sports fan.

CRITICAL INSTRUCTIONS:
1. NEVER modify, calculate or invent fantasy points. The deterministic Python engine has already computed the fantasy points impact:
Fantasy impact summary: {fantasy_impact.summary_sentence}
Player deltas: {[d.model_dump() for d in fantasy_impact.player_deltas]}

2. GROUNDING & EVIDENCE INTEGRITY:
- State strictly what happened based on the provided event data.
- Never invent ball-tracking, pitching spot, DRS projections, ultra-edge spikes, or umpire private discussions.
- Clearly list unavailable evidence.

EVENT DETAILS:
- Ball: {delivery.over_display} (Innings {delivery.innings})
- Batting: {delivery.team_batting} ({scoreboard.team_score}/{scoreboard.team_wickets} in {scoreboard.overs_display} ov)
- Striker: {delivery.batter} ({scoreboard.striker.runs} off {scoreboard.striker.balls})
- Bowler: {delivery.bowler} ({scoreboard.bowler.wickets}/{scoreboard.bowler.runs_conceded} in {scoreboard.bowler.overs} ov)
- Batter runs: {delivery.batter_runs}, Extras: {delivery.extra_runs} ({delivery.extra_type or 'none'}), Total runs: {delivery.total_runs}
- Is wicket: {delivery.is_wicket}, Kind: {delivery.wicket_kind}, Player out: {delivery.player_out}, Fielders: {delivery.fielders}
- Match context: {scoreboard.match_status}

Return a valid JSON object matching this schema:
{{
  "delivery_index": {delivery.index},
  "over_display": "{delivery.over_display}",
  "what_happened": "Clear explanation of the action on this delivery",
  "why_it_matters": "Match context and tactical stakes",
  "cricket_rule": {{
    "law_name": "Official Cricket Law name",
    "law_number": "MCC Law Number",
    "summary": "Plain English summary of the rule"
  }},
  "fantasy_impact": "Plain English explanation of who gained or lost fantasy points and why",
  "evidence": {{
    "grounded_in_data": ["Fact 1", "Fact 2"],
    "unavailable_evidence": ["Evidence not present in source data"]
  }},
  "fan_takeaway": "Punchy one-sentence summary for a fantasy fan",
  "engine_source": "gemini_ai"
}}
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        if response.text:
            data = json.loads(response.text)
            data["delivery_index"] = delivery.index
            data["over_display"] = delivery.over_display
            data["engine_source"] = "gemini_ai"
            return EventExplanation.model_validate(data)

        return None

