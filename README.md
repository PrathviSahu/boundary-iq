# BoundaryIQ — AI-Powered Cricket Match & Fantasy Companion

> **"Your match. Your players. Every moment explained."**

BoundaryIQ is an AI-powered cricket match companion for fantasy sports fans. It connects two specialized engines to solve the cricket fan's dilemma:
1. **Deterministic Cricket & Fantasy Engine (Python/FastAPI):** Calculates exact ball-by-ball match states, player statistics, and fantasy points using verified Dream11 T20 scoring rules. Pre-computes immutable snapshots in $O(1)$ lookup time so replay operations are instantaneous.
2. **AI Explanation Engine (Google Gen AI SDK):** Powered by `gemini-3.8-flash` via the official `google-genai` Python SDK, returning structured JSON schemas that explain cricket laws, match context, and fantasy impacts without ever fabricating ball-tracking evidence or inventing fantasy points.

---

## ⚡ Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │          React 18 + Vite UI            │
                      │  Tailwind CSS • Lucide • TypeScript    │
                      └──────────────────┬─────────────────────┘
                                         │ REST API
                                         ▼
                      ┌────────────────────────────────────────┐
                      │          FastAPI Backend Server        │
                      └──────────┬──────────────────┬──────────┘
                                 │                  │
                ┌────────────────┴──────┐   ┌───────┴─────────────────┐
                │ Deterministic Engine  │   │  AI Explanation Engine  │
                │ • O(1) Snapshot Index │   │  • google-genai SDK     │
                │ • Dream11 T20 Rules   │   │  • gemini-3.8-flash     │
                │ • Cricsheet Parser    │   │  • Evidence Boundaries  │
                │ • Cumulative Tracker  │   │  • Response Schema JSON │
                └──────────┬────────────┘   └───────┬─────────────────┘
                           │                        │
                           ▼                        ▼
                 Cricsheet JSON Match         Cache & Fallback
                 (ODC-BY 1.0 License)         (Deterministic Law)
```

---

## 🏏 Match Fixture & Data Source

- **Match:** ICC Men's T20 World Cup 2024 — Final
- **Teams:** India vs South Africa
- **Date:** 2024-06-29
- **Venue:** Kensington Oval, Bridgetown, Barbados
- **Result:** India won by 7 runs (India: 176/7, South Africa: 169/8)
- **Source File:** `data/ind_sa_t20wc_2024_final.json` (251 deliveries)
- **Data Attribution:** Ball-by-ball match data provided by [Cricsheet](https://cricsheet.org) under the **Open Data Commons Attribution License (ODC-BY 1.0)**. See `data/LICENSE.txt`.

### ⚠️ Grounding, Data Limitations & Cricsheet Audit
Cricsheet provides structured match events (runs, wickets, extras, fielder credits). However, it does **not** provide:
- Hawk-Eye ball tracking coordinate trajectories.
- Pitch map landing coordinates or release speed (km/h).
- Ultra-Edge / Snickometer audio waveforms.
- 3rd umpire DRS deliberation transcripts.
- Direct-hit telemetry for run-outs (Cricsheet records fielders involved in a dismissal, but does not identify whether the stumps were broken directly without an intermediary).

**BoundaryIQ Data Correctness Mandate:**
1. **Direct-Hit Run-Outs:** Because Cricsheet records fielders involved but does not verify direct-hit execution, BoundaryIQ **withholds the +12 direct-hit bonus** in the absence of verified source evidence and awards standard run-out credit (+6 pts each). Explanations explicitly disclose this evidence limitation.
2. **Non-Boundary Fours and Sixes:** Cricsheet's `runs.non_boundary` flag is strictly parsed. For overthrows or all-run fours/sixes, applicable batter run points (+4 or +6) are awarded, but boundary bonuses (+4 four bonus, +6 six bonus) are **withheld**.
3. **Maiden Overs:** Awarded **only for completed qualifying overs** (minimum 6 legal deliveries) with 0 runs conceded by the bowler. Truncated or incomplete overs are excluded. Byes and leg-byes are correctly excluded from bowler-conceded runs.
4. **Multiple Wicket Events:** The delivery parser inspects the entire `wickets` array, ensuring subsequent wicket records on a single delivery are never silently dropped.
5. **Zero Synthetic Physics:** BoundaryIQ strictly distinguishes source-verified facts from explanatory context and **never fabricates DRS, ball-tracking, or pitch trajectory data**. When an LBW dismissal occurs, BoundaryIQ explains MCC Law 36 and explicitly states that review coordinate evidence is absent in the source data.

---

## 🏆 Verified Fantasy Scoring Ruleset

- **Ruleset ID:** `dream11_standard_t20_v2025`
- **Version:** `2025.1.0` (Format: T20 Standard)
- **Official Source:** [Dream11 Point System](https://www.dream11.com/fantasy-cricket/point-system)
- **Retrospective Application Disclosure:** *Standard Dream11 T20 scoring rules are applied retrospectively to the ICC Men's T20 World Cup 2024 Final for analytics and demonstration purposes.*
- **Deterministic Implementation:** Python business logic in `app/scoring/ruleset.py` and `app/replay/engine.py`. Fantasy points are **never** calculated or altered by the LLM.

### Summary of Point Values (Dream11 Standard T20)
| Category | Event | Points | Condition / Notes |
| :--- | :--- | :--- | :--- |
| **General** | Starting XI Announcement | **+4 pts** | Awarded to all 22 named players |
| **General** | Captain Multiplier | **2.0x** | Points earned by selected Captain are doubled |
| **General** | Vice-Captain Multiplier | **1.5x** | Points earned by selected Vice-Captain multiplied by 1.5 |
| **Batting** | Run Scored | **+1 pt** | Per run scored off the bat |
| **Batting** | Boundary Four (4) Bonus | **+4 pts** | In addition to 4 runs (+8 pts total) |
| **Batting** | Boundary Six (6) Bonus | **+6 pts** | In addition to 6 runs (+12 pts total) |
| **Batting** | 25 Run Milestone Bonus | **+4 pts** | Awarded exactly once upon crossing 25 runs |
| **Batting** | Half-Century (50+ runs) | **+8 pts** | Replaces 25-run bonus (non-stacking: +8 total) |
| **Batting** | 75-Run Milestone Bonus | **+12 pts** | Replaces 50-run bonus (non-stacking: +12 total) |
| **Batting** | Century (100+ runs) | **+16 pts** | Replaces 75-run bonus (non-stacking: +16 total) |
| **Batting** | Duck Penalty | **-2 pts** | Dismissal on 0 runs (BAT, WK, AR only; not pure BOWL) |
| **Batting** | Strike Rate (> 170.0) | **+6 pts** | Min 10 balls faced (not applicable for BOWL) |
| **Batting** | Strike Rate (150 - 170) | **+4 pts** | Min 10 balls faced |
| **Batting** | Strike Rate (130 - 150) | **+2 pts** | Min 10 balls faced |
| **Batting** | Strike Rate (60 - 70) | **-2 pts** | Min 10 balls faced |
| **Batting** | Strike Rate (50 - 59.99) | **-4 pts** | Min 10 balls faced |
| **Batting** | Strike Rate (< 50.0) | **-6 pts** | Min 10 balls faced |
| **Bowling** | Wicket (excl. Run Out) | **+30 pts** | Per dismissal credited to bowler |
| **Bowling** | Bowled / LBW Bonus | **+8 pts** | Added to wicket points (+38 pts total) |
| **Bowling** | Dot Ball Bowled | **+1 pt** | Per legal delivery with 0 runs conceded by bowler |
| **Bowling** | 3-Wicket Haul Bonus | **+4 pts** | Awarded exactly once at 3 wickets |
| **Bowling** | 4-Wicket Haul Bonus | **+8 pts** | Replaces 3-wicket bonus (non-stacking: +8 total) |
| **Bowling** | 5-Wicket Haul Bonus | **+12 pts** | Replaces 4-wicket bonus (non-stacking: +12 total) |
| **Bowling** | Maiden Over | **+12 pts** | 0 runs conceded by bowler in completed over |
| **Bowling** | Economy (< 5.0 RPO) | **+6 pts** | Min 2 overs (12 legal balls) bowled |
| **Bowling** | Economy (5.0 - 5.99) | **+4 pts** | Min 2 overs bowled |
| **Bowling** | Economy (6.0 - 7.0) | **+2 pts** | Min 2 overs bowled |
| **Bowling** | Economy (10.0 - 11.0) | **-2 pts** | Min 2 overs bowled |
| **Bowling** | Economy (11.01 - 12.0) | **-4 pts** | Min 2 overs bowled |
| **Bowling** | Economy (> 12.0 RPO) | **-6 pts** | Min 2 overs bowled |
| **Fielding** | Catch Taken | **+8 pts** | Per clean catch |
| **Fielding** | 3-Catch Bonus | **+4 pts** | Awarded upon taking 3rd catch in match |
| **Fielding** | Stumping | **+12 pts** | Credited to wicket-keeper |
| **Fielding** | Direct Run Out | **+12 pts** | Credited when confirmed by verified source evidence |
| **Fielding** | Run Out (Standard/Shared) | **+6 pts** | Credited to involved fielders (default when direct-hit is unverified) |
| **Multipliers**| Captain (C) | **2.0x** | Applied to base points without mutating records |
| **Multipliers**| Vice-Captain (VC) | **1.5x** | Applied to base points without mutating records |

---

## 🤖 AI Integration & Rate-Limiting Controls

- **SDK:** Official Google Gen AI Python SDK (`google-genai`).
- **Model:** `gemini-3.8-flash` (configurable via `GEMINI_MODEL`).
- **Output:** Structured Pydantic JSON validation (`EventExplanation`).
- **In-Memory Caching:** `(match_id, delivery_index, ruleset_version)` prevents duplicate API invocations.
- **Autoplay Protection:** During rapid replay scrubbing or autoplay, instant deterministic summaries are served in $O(1)$ without flooding the Gemini API. Live AI generation triggers when paused or upon clicking key moments.
- **Graceful Fallback:** If `GEMINI_API_KEY` is not configured or an API error occurs, BoundaryIQ serves comprehensive, MCC Law-grounded deterministic explanations with `engine_source="deterministic_rules_engine"`.

---

## 🚀 Quickstart & Run Commands

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
cd boundary-iq/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# (Optional) Set your Gemini API Key in .env
echo "GEMINI_API_KEY=your_key_here" >> .env
echo "GEMINI_MODEL=gemini-3.8-flash" >> .env

# Run pytest unit tests (42 tests)
pytest -v

# Start FastAPI server on port 8001
uvicorn app.main:app --port 8001
```

### 3. Frontend Setup
```bash
cd boundary-iq/frontend
npm install
npm run build
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🧪 Test Suite

The test suite consists of 42 unit tests across scoring, replay, snapshots, Cricsheet data correctness, and API:
```bash
cd boundary-iq/backend
./venv/bin/pytest -v
```
Test categories include:
- `test_boundaries_scoring`: Boundary 4s and 6s point calculations.
- `test_cricsheet_correctness`: Non-boundary fours/sixes, unverified direct-hit run-outs, completed maiden overs, and multi-wicket event parsing.
- `test_wickets_and_bowled_bonus`: Wickets, LBW, and bowled bonuses.
- `test_milestone_awarded_exactly_once`: Verifies 30/50 run milestones trigger once and never duplicate.
- `test_captain_and_vice_captain_immutability`: Ensures 2x/1.5x multipliers apply without mutating player base scores.
- `test_snapshot_o1_retrieval`: Forward and backward stepping consistency in $O(1)$.
- `test_key_moments_filters`: Pre-indexed key moments (wickets, boundaries, milestones).
- `test_explain_endpoint`: Evidence boundaries and absence of DRS hallucinations.

---

## ⚖️ Legal & Attribution Disclaimer

BoundaryIQ is an independent research prototype developed for sports analytics and product demonstration.
- It is **not** affiliated with, endorsed by, or sponsored by **Dream11**, **Sporta Technologies Pvt. Ltd.**, **BCCI**, **ICC**, or any cricket governing body.
- Ball-by-ball match data is provided by **Cricsheet** (https://cricsheet.org) under the **Open Data Commons Attribution License (ODC-BY 1.0)**.

