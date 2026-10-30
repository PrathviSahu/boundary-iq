# BoundaryIQ — AI-Powered Cricket Match & Fantasy Companion

> **"Your match. Your players. Every moment explained."**

BoundaryIQ is an AI-powered cricket match replay and fantasy companion designed for live sports fans. Built for the **Dream11 Forward Deployed Engineer Intern** assignment, it bridges the gap between fast-moving cricket broadcasts and complex fantasy sports calculations.

---

## 📌 Executive Summary: Dream11 FDE Evaluation

### 1. What fan problem does Boundary IQ solve?
During a live, high-stakes T20 match, fantasy cricket fans face cognitive overload and anxiety. While broadcast feeds provide raw scores and commentary, and fantasy apps display aggregate leaderboard point totals, neither platform answers the three critical questions every fan asks when the game turns:
1. **What just happened?** Why was that delivery tactically significant?
2. **Why did my fantasy points change?** Which player on my squad earned or lost points, and under which specific scoring rule?
3. **What could I have done differently?** How much is my captaincy choice costing me right now compared to the optimal lineup?

BoundaryIQ solves this by providing ball-by-ball transparency, combining deterministic scoring with natural language tactical context.

### 2. How does the product help fans?
- **"Why My Points Changed" Ball Delta Badges:** Fans immediately see per-player impact on the active delivery (e.g. `+58.5 pts [VC 1.5x]` with granular subtext: *Dot ball bowled (+1), Wicket taken (+30), Bowled/LBW bonus (+8)*).
- **"What-If Captaincy" Instant Regret Calculator:** Evaluates all possible Captain (2x) and Vice-Captain (1.5x) combinations up to the current delivery in $O(11 \log 11)$ time, calculating the exact point regret delta (e.g., `+21 PTS DIFF` if Bumrah had been Captain instead of Rohit).
- **3-Pillar Scannable Explainer:** Breaks down each moment into three quick-to-read sections:
  1. *Tactical Context:* Match stakes, run rate pressure, and pitch dynamics.
  2. *Fantasy Impact:* Active squad point deltas with multiplier breakdowns.
  3. *Next-Ball Watchout:* Tactical matchups and momentum triggers to watch on the very next ball.
- **Zero-Hallucination Integrity:** Pure separation of concerns. Fantasy points and match stats are computed deterministically from verified source data; LLMs never calculate, estimate, or modify point scores.

### 3. Which AI tools and models were used?
- **Model:** `gemini-2.5-flash` / `gemini-3.5-flash-lite` via the official Google Gen AI Python SDK (`google-genai`).
- **Structured Schema:** Strict Pydantic JSON schema (`EventExplanation`) enforcing four distinct fields: summary, tactical context, fantasy impact, and next-ball watchout.
- **Production Guardrails:**
  - Bounded concurrency with a 4-worker thread pool and non-blocking admission semaphore to prevent overload.
  - Squad-isolated LRU Cache (capacity 500) keyed by `(match_id, delivery_index, ruleset, captain, vice_captain)`.
  - Curated deterministic fallback explanations for 5 iconic turning points (Bumrah's wickets, Suryakumar's catch, Klaasen's counter-attack, and Kohli's 76) ensuring instant, high-quality responses even during network interruptions.

---

## ⚡ Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │          React 18 + Vite UI            │
                      │  Tailwind CSS • Lucide • TypeScript    │
                      │  • Ball Delta Badges & Regret Card     │
                      │  • 3-Pillar Scannable Explainer        │
                      └──────────────────┬─────────────────────┘
                                         │ REST API
                                         ▼
                      ┌────────────────────────────────────────┐
                      │          FastAPI Backend Server        │
                      │  • Proxy-Safe Rate Limiter (Sliding)   │
                      │  • 100 KB Payload Guard • /api/ready   │
                      └──────────┬──────────────────┬──────────┘
                                 │                  │
                ┌────────────────┴──────┐   ┌───────┴─────────────────┐
                │ Deterministic Engine  │   │  AI Explanation Engine  │
                │ • O(1) Snapshot Index │   │  • google-genai SDK     │
                │ • Dream11 T20 Rules   │   │  • gemini-3.5-flash-lite│
                │ • What-If Regret Calc │   │  • Bounded Worker Pool  │
                │ • Cricsheet Parser    │   │  • LRU Cache (Cap: 500) │
                └──────────┬────────────┘   └───────┬─────────────────┘
                           │                        │
            ┌──────────────┴──────────────┐         ▼
            ▼                             ▼    Curated Fallback
  Cricsheet Match JSON             SQLite Database  (5 Iconic Moments)
  (ODC-BY 1.0 License)         (WAL Mode • Teams)
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

## 🛡️ Production Readiness & Resilience

Phase 2 hardened BoundaryIQ for live production deployment:

1. **Persistent SQLite Database:**
   - Managed via Python standard library `sqlite3` (`app/db/repository.py`) with zero external ORM overhead.
   - Configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and `PRAGMA synchronous=NORMAL` for concurrent reads/writes and crash resilience.
   - User-customized fantasy squads survive server restarts and scale seamlessly.
2. **Proxy-Safe Security & Rate Limiting:**
   - Reads the leftmost untrusted IP from `X-Forwarded-For` when behind proxies (Render, Cloudflare, AWS ALB), preventing rate limit spoofing.
   - Sliding-window algorithm bounds burst traffic.
   - Request size limiting middleware rejects payloads $> 100\text{ KB}$ with HTTP 413.
3. **Health & Readiness Endpoints:**
   - `/api/health`: Immediate liveness check reporting uptime, match engine status, and database connectivity.
   - `/api/ready`: Readiness probe verifying data file integrity, snapshot pre-computation (251 deliveries), and database read/write health.
4. **Cloud Deployment Artifacts:**
   - Root `Procfile` and `backend/Procfile` configured for zero-configuration deployment on Render, Railway, or Heroku.
   - Frontend includes automatic cold-start detection: displays a friendly spinner and status banner if the backend is waking from serverless hibernation.

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
echo "GEMINI_MODEL=gemini-3.5-flash-lite" >> .env

# Run pytest unit & regression tests (91 tests)
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

## 🧪 Comprehensive Test Suite

BoundaryIQ is backed by **91 passing backend unit, regression, and security tests**, alongside automated Playwright browser E2E tests:

```bash
cd boundary-iq/backend
./venv/bin/pytest -v
```

### Backend Test Coverage Breakdown (91 Tests)
- `test_production_readiness.py` (7 tests): SQLite persistence across reboots, What-If Captaincy calculation correctness, 3-pillar response schema validation, `/api/ready` readiness probe, payload limit (HTTP 413), proxy IP parsing, and curated iconic moment fallback reliability.
- `test_phase1_regressions.py` (2 tests): LRU cache eviction boundary (500 entries) and executor admission control / semaphore release.
- `test_api.py` (10 tests): Health check, match metadata, deliveries, snapshot retrieval, key moments, player rosters, ruleset verification, fantasy squad persistence, and team score computation.
- `test_cricsheet_correctness.py` (16 tests): Non-boundary fours/sixes (overthrows / all-run boundaries with bonus withheld), unverified direct-hit run-outs, completed 6-ball maiden over rules, multi-wicket deliveries, no-ball boundaries, and shared fielder points.
- `test_fantasy_engine.py` (10 tests): Dream11 standard scoring logic covering starting XI bonus, captain (2x) and vice-captain (1.5x) multipliers, batting milestones, duck penalties, dot ball rewards, wicket & LBW/bowled bonuses, catches, and bowling wicket hauls.
- `test_replay_engine.py` (11 tests): Pre-computed snapshot state consistency, step back/forward determinism, captaincy immutability, key moment categorization, and Cricsheet delivery audit attributes.
- `test_security.py` (8 tests): Security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options), CORS exact origin allowlisting, project-scoped Vercel preview regex matching, untrusted origin rejection, and sliding window rate limiting.
- `test_reliability.py` (27 tests): Delivery boundary validation, match ID isolation, cache key squad fingerprinting, negative indexing guards, and executor concurrency limits.

### Automated Verification Script
Run the end-to-end product verification suite:
```bash
cd boundary-iq/backend
./venv/bin/python verify_product.py
```
*Validates match metadata, 251 delivery snapshots, key moments, fantasy ruleset, custom squad persistence, team scores, and deterministic explanations across 7 automated test suites.*

### Frontend E2E Race Condition & Scrubbing Test
Run the Playwright asynchronous sequence and cancellation verification:
```bash
python3 frontend/tests/e2e/test_race_conditions.py
```
*Simulates rapid scrubbing across deliveries, verifying `AbortController` cancellation, monotonic request ID ordering, and UI state consistency.*

---

## ⚖️ Legal & Attribution Disclaimer

BoundaryIQ is an independent research prototype developed for sports analytics and product demonstration for the Dream11 Forward Deployed Engineer Intern assignment.
- It is **not** affiliated with, endorsed by, or sponsored by **Dream11**, **Sporta Technologies Pvt. Ltd.**, **BCCI**, **ICC**, or any cricket governing body.
- Ball-by-ball match data is provided by **Cricsheet** (https://cricsheet.org) under the **Open Data Commons Attribution License (ODC-BY 1.0)**.
