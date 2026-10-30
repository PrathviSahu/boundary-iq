import os
import re
import json
import hashlib
import logging
import threading
import concurrent.futures
from collections import OrderedDict
from typing import Dict, Tuple, Optional, Any, List
from app.models.match import Delivery, SnapshotState
from app.models.fantasy import BallFantasyImpact, FantasyTeamConfig
from app.models.explanation import (
    EventExplanation, RuleExplanation, EvidenceBoundary
)

# Module-level bounded thread pool and admission semaphore for Gemini calls.
# max_workers=4 caps concurrent in-flight HTTP calls;
# _GEMINI_SEMAPHORE limits admitted tasks so pending requests fail-fast to deterministic
# fallback instead of accumulating in an unbounded queue.
_MAX_GEMINI_WORKERS = 4
_GEMINI_SEMAPHORE = threading.Semaphore(_MAX_GEMINI_WORKERS)
_GEMINI_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=_MAX_GEMINI_WORKERS, thread_name_prefix="gemini_worker"
)
MAX_CACHE_SIZE = 500


def _team_fingerprint(team: FantasyTeamConfig) -> str:
    """Return a stable SHA-256 hex digest (16 chars) of the full team config.

    Covers selected_players (sorted), captain, and vice_captain so that any
    meaningful difference in fantasy configuration produces a different cache key.
    """
    stable = {
        "players": sorted(team.selected_players),
        "captain": team.captain,
        "vice_captain": team.vice_captain,
    }
    payload = json.dumps(stable, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]

logger = logging.getLogger(__name__)

CRICKET_LAW_CATALOG: Dict[str, Dict[str, str]] = {
    "bowled": {
        "law_name": "Bowled",
        "law_number": "MCC Law 32",
        "summary": "The striker is out Bowled if the wicket is put down by a ball delivered by the bowler, not being a No ball. Directly penetrates the batter's defense and breaks the wicket."
    },
    "caught": {
        "law_name": "Caught",
        "law_number": "MCC Law 33",
        "summary": "The striker is out Caught if the ball delivered by the bowler touches his bat without previously touching an umpire or fielder, and is held cleanly by a fielder before touching the ground."
    },
    "lbw": {
        "law_name": "Leg Before Wicket (LBW)",
        "law_number": "MCC Law 36",
        "summary": "The striker is out LBW if the ball pitches in line or outside off-stump, is intercepted by the batter's body without bat contact, and would have continued to hit the stumps."
    },
    "run out": {
        "law_name": "Run Out",
        "law_number": "MCC Law 38",
        "summary": "A batter is out Run Out if, at any time while the ball is in play, they are out of their ground and their wicket is broken by an opponent fielder."
    },
    "stumped": {
        "law_name": "Stumped",
        "law_number": "MCC Law 39",
        "summary": "The striker is out Stumped if the delivery is not a No ball, the striker is out of their ground receiving the delivery, and the wicket-keeper breaks the wicket without the striker attempting a run."
    },
    "four": {
        "law_name": "Boundary Four",
        "law_number": "MCC Law 19",
        "summary": "A boundary 4 is awarded when a struck ball reaches or crosses the boundary rope having touched the ground inside the field of play."
    },
    "six": {
        "law_name": "Boundary Six (Maximum)",
        "law_number": "MCC Law 19",
        "summary": "A boundary 6 is scored when the struck ball clears the boundary rope on the full without touching the ground inside the playing field."
    },
    "wides": {
        "law_name": "Wide Ball",
        "law_number": "MCC Law 22",
        "summary": "An illegal delivery judged to have passed beyond the striker's reach. 1 penalty run is conceded to the batting team, does not count as a legal ball, and must be rebowled."
    },
    "noballs": {
        "law_name": "No Ball",
        "law_number": "MCC Law 21",
        "summary": "An illegal delivery (foot overstepping or dangerous height). 1 run penalty, does not count towards the 6-ball over, and awards a Free Hit on the next delivery in T20."
    },
    "dot": {
        "law_name": "Scoring Runs / Defense",
        "law_number": "MCC Law 18",
        "summary": "A legal delivery on which no runs are conceded and no wicket falls. Key component of building bowling pressure in T20 death overs."
    },
    "standard_run": {
        "law_name": "Scoring Runs",
        "law_number": "MCC Law 18",
        "summary": "Batters score runs by running between their creases after striking the ball or through overthrows."
    }
}

class AIExplanationService:
    def __init__(self, max_cache_size: int = MAX_CACHE_SIZE):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
        self.max_cache_size = max_cache_size
        self._cache_lock = threading.Lock()
        # Bounded LRU cache: (match_id, delivery_index, ruleset_version, team_fingerprint) -> EventExplanation
        self.cache: "OrderedDict[Tuple[str, int, str, str], EventExplanation]" = OrderedDict()
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Google Gen AI client with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Gen AI client: {e}")

    def _get_from_cache(self, key: Tuple[str, int, str, str]) -> Optional[EventExplanation]:
        with self._cache_lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return None

    def _put_in_cache(self, key: Tuple[str, int, str, str], value: EventExplanation) -> None:
        with self._cache_lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.max_cache_size:
                self.cache.popitem(last=False)  # Evict oldest entry (LRU)

    def explain_delivery(
        self,
        match_id: str,
        delivery: Delivery,
        snapshot: SnapshotState,
        fantasy_impact: BallFantasyImpact,
        team_config: FantasyTeamConfig,
        ruleset_version: str = "2024.3.0",
        force_refresh: bool = False
    ) -> EventExplanation:
        fingerprint = _team_fingerprint(team_config)
        cache_key = (match_id, delivery.index, ruleset_version, fingerprint)

        # Check cache
        if not force_refresh:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached

        # If Gemini client is active, attempt AI generation with strict timeout & error sanitation
        if self.client and self.api_key:
            try:
                ai_result = self._call_gemini(delivery, snapshot, fantasy_impact, ruleset_version)
                if ai_result:
                    self._put_in_cache(cache_key, ai_result)
                    return ai_result
            except Exception as e:
                sanitized_err = re.sub(r'([?&]key=|token=|bearer\s+)[^\s&]+', r'\1[REDACTED]', str(e), flags=re.IGNORECASE)
                logger.warning(f"Gemini API generation failed for ball {delivery.index}: {sanitized_err}. Using deterministic fallback.")

        # Grounded Deterministic Fallback
        deterministic_result = self._generate_deterministic_explanation(
            delivery, snapshot, fantasy_impact
        )
        self._put_in_cache(cache_key, deterministic_result)
        return deterministic_result

    def _generate_deterministic_explanation(
        self,
        delivery: Delivery,
        snapshot: SnapshotState,
        fantasy_impact: BallFantasyImpact
    ) -> EventExplanation:
        # 1. Determine Law
        law_key = "standard_run"
        if delivery.is_wicket:
            law_key = delivery.wicket_kind or "caught"
        elif delivery.is_six:
            law_key = "six"
        elif delivery.is_four:
            law_key = "four"
        elif delivery.extra_type:
            law_key = delivery.extra_type
        elif delivery.is_dot:
            law_key = "dot"

        law = CRICKET_LAW_CATALOG.get(law_key, CRICKET_LAW_CATALOG["standard_run"])

        # 2. Formulate Headline & What Happened
        if delivery.is_wicket:
            if delivery.wickets and len(delivery.wickets) > 1:
                outs = [f"{w.player_out} ({w.kind})" for w in delivery.wickets]
                headline = f"DOUBLE WICKET! Multiple dismissals: {', '.join(outs)}!"
                what_happened = f"Extraordinary multi-wicket sequence on delivery {delivery.over_display}: {', '.join(outs)} off {delivery.bowler}."
                simple_cricket = "Official cricket laws recognize multiple dismissals occurring in continuous action on a single delivery (e.g., striker dismissed followed by a run-out of non-striker)."
            elif delivery.wicket_kind == "caught":
                f_name = delivery.fielders[0] if delivery.fielders else "fielder"
                headline = f"WICKET! {delivery.player_out} caught by {f_name}!"
                what_happened = f"{delivery.bowler} bowls to {delivery.player_out}; false attacking stroke mistimed and caught cleanly by {f_name}."
                simple_cricket = f"Under cricket laws, once the ball touches the bat, a fielder holding the ball cleanly before it contacts the ground completes a fair dismissal."
            elif delivery.wicket_kind in ("bowled", "lbw"):
                headline = f"TIMBER! {delivery.player_out} {delivery.wicket_kind.upper()} by {delivery.bowler}!"
                what_happened = f"{delivery.bowler} penetrates {delivery.player_out}'s defense with pinpoint line and length."
                simple_cricket = f"Clean dismissal breaking the wicket. For LBW, the ball must pitch legally, strike the pads in line, and be projected to hit the stumps."
            elif delivery.wicket_kind == "run out":
                f_name = " & ".join(delivery.fielders) if delivery.fielders else "fielding unit"
                headline = f"RUN OUT! {delivery.player_out} caught short of the crease!"
                what_happened = f"High-pressure running between wickets. {f_name} breaks the stumps while {delivery.player_out} is out of his crease (direct-hit unverified from source data)."
                simple_cricket = "Batters must ground their bat or body behind the popping crease before the fielder legally breaks the stumps."
            else:
                headline = f"WICKET! {delivery.player_out} dismissed ({delivery.wicket_kind})!"
                what_happened = f"{delivery.player_out} dismissed off the bowling of {delivery.bowler}."
                simple_cricket = f"Dismissal registered under official {law['law_name']} regulations."
        elif delivery.non_boundary and delivery.batter_runs in (4, 6):
            headline = f"{delivery.batter_runs} RUNS! {delivery.batter} scores (Non-Boundary / Overthrows)"
            what_happened = f"{delivery.batter} scores {delivery.batter_runs} runs through running between wickets or overthrows without the ball crossing the boundary rope."
            simple_cricket = "Under MCC Law 18, runs completed by running or overthrows without contacting the perimeter boundary are non-boundary runs and do not qualify for boundary bonuses."
        elif delivery.is_six:
            headline = f"MAXIMUM! 6 Runs launched by {delivery.batter}!"
            what_happened = f"{delivery.batter} meets {delivery.bowler}'s delivery with power, clearing the boundary ropes on the full."
            simple_cricket = "Ball hit directly over the perimeter boundary without bouncing awards the maximum 6 runs."
        elif delivery.is_four:
            headline = f"CRACKING FOUR! {delivery.batter} finds the fence!"
            what_happened = f"{delivery.batter} pierces the infield off {delivery.bowler}, ball racing across the turf to the boundary rope."
            simple_cricket = "Ball touches the turf inside the boundary before making contact with or crossing the perimeter rope."
        elif delivery.extra_type:
            headline = f"EXTRA! {delivery.extra_runs} {delivery.extra_type.upper()} conceded by {delivery.bowler}."
            what_happened = f"{delivery.bowler} delivers an illegal delivery ({delivery.extra_type}), gifting {delivery.extra_runs} penalty runs."
            simple_cricket = f"Official {law['law_name']} rules deem this ball illegal; 1 penalty run is awarded and must be rebowled."
        elif delivery.is_dot:
            headline = f"DOT BALL: {delivery.bowler} beats {delivery.batter}!"
            what_happened = f"Pace and precision from {delivery.bowler}. {delivery.batter} unable to score."
            simple_cricket = "Defensive play yielding 0 runs, keeping batsman under dot-ball pressure."
        else:
            headline = f"{delivery.batter_runs} Run(s) scored by {delivery.batter}."
            what_happened = f"{delivery.batter} works {delivery.bowler} into the outfield for {delivery.batter_runs} run(s)."
            simple_cricket = "Batters complete running between the 22-yard creases."

        # 3. Why It Matters (Match context)
        if delivery.innings == 2 and snapshot.runs_needed is not None:
            if delivery.is_wicket:
                why_it_matters = f"Crucial breakthrough in the chase! {snapshot.batting_team} is now {snapshot.team_score}/{snapshot.team_wickets}. They need {snapshot.runs_needed} runs from {snapshot.balls_remaining} balls (Req RR: {snapshot.required_run_rate})."
            elif delivery.is_six or delivery.is_four:
                why_it_matters = f"Momentum surge for {snapshot.batting_team}! Boundary brings equation down to {snapshot.runs_needed} runs needed from {snapshot.balls_remaining} balls."
            else:
                why_it_matters = f"Chase progression: {snapshot.batting_team} stands at {snapshot.team_score}/{snapshot.team_wickets} after {snapshot.overs_display} overs (Target: {snapshot.target})."
        else:
            if delivery.is_wicket:
                why_it_matters = f"Innings 1 blow: {snapshot.batting_team} loses a key batter at {snapshot.team_score}/{snapshot.team_wickets} in {snapshot.overs_display} overs."
            elif delivery.is_six or delivery.is_four:
                why_it_matters = f"Run rate boost: Current run rate elevates to {snapshot.run_rate} RPO."
            else:
                why_it_matters = f"First innings scoreboard building: {snapshot.team_score}/{snapshot.team_wickets} in {snapshot.overs_display} ov."

        # 4. Fantasy Impact Explanation
        if fantasy_impact.player_deltas:
            delta_lines = []
            for d in fantasy_impact.player_deltas:
                c_tag = " [C 2x]" if d.is_captain else " [VC 1.5x]" if d.is_vice_captain else ""
                sign = "+" if d.net_delta > 0 else ""
                delta_lines.append(f"{d.player_name}{c_tag}: {sign}{d.net_delta} pts ({d.reason}, new total: {d.new_total} pts)")
            fantasy_impact_exp = "Fantasy points updated: " + "; ".join(delta_lines) + f". Team Impact: {'+' if fantasy_impact.fantasy_team_delta >= 0 else ''}{fantasy_impact.fantasy_team_delta} pts."
        else:
            fantasy_impact_exp = "No fantasy scoring criteria triggered on this delivery."

        # 5. Evidence Boundaries & Data Limitations
        grounded = [
            f"Official match record: Delivery {delivery.over_display} (Innings {delivery.innings})",
            f"Batter: {delivery.batter}, Bowler: {delivery.bowler}",
            f"Runs scored: {delivery.batter_runs} off bat, {delivery.extra_runs} extras (Total: {delivery.total_runs})"
        ]
        if delivery.non_boundary:
            grounded.append("Cricsheet 'non_boundary: true' flag recorded: runs scored without contacting boundary fence; boundary bonuses withheld.")
        if delivery.is_wicket:
            if delivery.wickets and len(delivery.wickets) > 1:
                for w in delivery.wickets:
                    grounded.append(f"Official dismissal: {w.player_out} ({w.kind})")
                    if w.fielders:
                        grounded.append(f"Fielding assist: {', '.join(w.fielders)}")
            else:
                grounded.append(f"Official dismissal type: {delivery.wicket_kind} (Player out: {delivery.player_out})")
                if delivery.fielders:
                    grounded.append(f"Fielding assist credited: {', '.join(delivery.fielders)}")

        unavailable = [
            "Source dataset does not supply Hawkeye or ball-tracking coordinate evidence.",
            "Pitch map location and release speed (km/h) are not recorded in Cricsheet data.",
            "Ultra-Edge / Snickometer audio waveforms are unavailable."
        ]
        if delivery.is_wicket and delivery.wicket_kind == "lbw":
            unavailable.append("DRS tracking (pitching line, impact line, hitting stumps) cannot be verified from source records.")
        if delivery.is_wicket and delivery.wicket_kind == "run out":
            unavailable.append("Source dataset identifies fielders involved in a dismissal, but does not establish whether the run-out was a direct hit. Direct-hit bonus (+12 pts) is withheld in favor of standard run-out credit (+6 pts).")

        data_limits = [
            "Cricsheet ball-by-ball data does not include delivery video, radar speed, or Hawkeye trajectories.",
            "All fantasy point calculations are strictly grounded in deterministic rules logic."
        ]
        if delivery.is_wicket and delivery.wicket_kind == "run out":
            data_limits.append("Cricsheet fielders list indicates participation, not direct-hit execution. Direct-hit bonuses require verified evidence.")

        fan_takeaway = f"Ball {delivery.over_display} — {delivery.summary}"

        return EventExplanation(
            delivery_index=delivery.index,
            over_display=delivery.over_display,
            headline=headline,
            what_happened=what_happened,
            simple_cricket_explanation=simple_cricket,
            why_it_matters=why_it_matters,
            fantasy_impact_explanation=fantasy_impact_exp,
            cricket_rule=RuleExplanation(
                law_name=law["law_name"],
                law_number=law["law_number"],
                summary=law["summary"]
            ),
            evidence=EvidenceBoundary(
                grounded_in_data=grounded,
                unavailable_evidence=unavailable
            ),
            data_limitations=data_limits,
            fan_takeaway=fan_takeaway,
            engine_source="deterministic_rules_engine"
        )

    def _call_gemini(
        self,
        delivery: Delivery,
        snapshot: SnapshotState,
        fantasy_impact: BallFantasyImpact,
        ruleset_version: str
    ) -> Optional[EventExplanation]:
        from google.genai import types

        prompt = f"""
You are the AI cricket explanation engine for BoundaryIQ.
Your task: Explain this specific cricket ball delivery to a fantasy sports fan.

CRITICAL INSTRUCTIONS:
1. NEVER modify, calculate or invent fantasy points. The deterministic Python engine has already computed the fantasy points impact:
Fantasy impact: {fantasy_impact.summary_sentence}
Player deltas: {[d.model_dump() for d in fantasy_impact.player_deltas]}

2. GROUNDING & EVIDENCE INTEGRITY:
- State strictly what happened based on the provided event data.
- Never invent ball-tracking, pitching spot, DRS projections, ultra-edge spikes, or umpire private discussions.
- If non_boundary is true, clarify that runs resulted from running or overthrows, not crossing the boundary line.
- If a run-out occurs, do not state it was a direct hit unless direct_hit is explicitly True in the event details.
- When an LBW dismissal occurs, explain the general LBW law and explicitly note that actual review evidence is unavailable in the dataset.
- Distinguish source-provided facts from explanatory context.

EVENT DETAILS:
- Ball: {delivery.over_display} (Innings {delivery.innings})
- Match: {snapshot.batting_team} ({snapshot.team_score}/{snapshot.team_wickets} in {snapshot.overs_display} ov) vs {snapshot.bowling_team}
- Striker: {delivery.batter} ({snapshot.striker.runs} off {snapshot.striker.balls} balls)
- Bowler: {delivery.bowler} ({snapshot.bowler.wickets}/{snapshot.bowler.runs_conceded} in {snapshot.bowler.overs} ov)
- Runs off bat: {delivery.batter_runs}, Extras: {delivery.extra_runs} ({delivery.extra_type or 'none'}), Total runs: {delivery.total_runs}
- Non-boundary: {delivery.non_boundary} (boundary bonus applies only if false)
- Is maiden over completing ball: {delivery.is_maiden_completing_ball}
- Is wicket: {delivery.is_wicket}, Kind: {delivery.wicket_kind}, Player out: {delivery.player_out}, Fielders: {delivery.fielders}
- Direct-hit evidence: {delivery.direct_hit}
- All wickets on delivery: {[w.model_dump() for w in delivery.wickets]}
- Match situation: {snapshot.match_status}
- Ruleset version: {ruleset_version}
"""

        timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "8.0"))

        def _invoke():
            return self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EventExplanation,
                    temperature=0.2,
                ),
            )

        # Bounded admission: if all 4 worker slots are occupied, fail-fast
        # immediately to deterministic fallback rather than queueing unboundedly.
        acquired = _GEMINI_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            logger.warning(
                f"Gemini executor saturated (all {_MAX_GEMINI_WORKERS} workers busy). "
                f"Fast-failing to deterministic fallback for ball {delivery.index}."
            )
            return None

        def _wrapped_invoke():
            try:
                return _invoke()
            finally:
                _GEMINI_SEMAPHORE.release()

        try:
            future = _GEMINI_EXECUTOR.submit(_wrapped_invoke)
        except Exception:
            _GEMINI_SEMAPHORE.release()
            raise

        done, _ = concurrent.futures.wait([future], timeout=timeout_seconds)
        if not done:
            logger.warning(
                f"Gemini API request timed out after {timeout_seconds}s "
                f"for ball {delivery.index}. Background worker slot remains held until completion."
            )
            future.cancel()  # No-op if running; prevents dispatch if queued.
            return None

        response = future.result()

        if response and response.text:
            data = json.loads(response.text)
            data["delivery_index"] = delivery.index
            data["over_display"] = delivery.over_display
            data["engine_source"] = "gemini_ai"
            return EventExplanation.model_validate(data)

        return None

