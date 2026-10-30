export interface Fielder {
  name: string;
}

export interface Delivery {
  index: number;
  innings: number;
  team_batting: string;
  team_bowling: string;
  over: number;
  ball_in_over: number;
  over_display: string;
  batter: string;
  bowler: string;
  non_striker: string;
  batter_runs: number;
  extra_runs: number;
  total_runs: number;
  extra_type?: string | null;
  non_boundary?: boolean;
  is_wicket: boolean;
  wicket_kind?: string | null;
  player_out?: string | null;
  fielders: string[];
  direct_hit?: boolean | null;
  wickets?: { kind: string; player_out: string; fielders: string[] }[];
  is_four: boolean;
  is_six: boolean;
  is_dot: boolean;
  is_maiden_completing_ball: boolean;
  summary: string;
}

export interface BatterLiveStats {
  name: string;
  runs: number;
  balls: number;
  fours: number;
  sixes: number;
  strike_rate: number;
  is_out: boolean;
  dismissal_desc?: string | null;
}

export interface BowlerLiveStats {
  name: string;
  overs: number;
  legal_balls: number;
  maidens: number;
  runs_conceded: number;
  wickets: number;
  economy: number;
}

export interface RecentBall {
  index: number;
  over_display: string;
  total_runs: number;
  is_wicket: boolean;
  is_four: boolean;
  is_six: boolean;
  extra_type?: string | null;
}

export interface KeyMoment {
  delivery_index: number;
  over_display: string;
  category: string;
  title: string;
  subtitle: string;
  points_headline?: string | null;
}

export interface SnapshotState {
  delivery_index: number;
  over_display: string;
  innings: number;
  batting_team: string;
  bowling_team: string;
  team_score: number;
  team_wickets: number;
  overs_display: string;
  legal_balls_bowled: number;
  run_rate: number;
  target?: number | null;
  required_run_rate?: number | null;
  runs_needed?: number | null;
  balls_remaining?: number | null;
  striker: BatterLiveStats;
  non_striker?: BatterLiveStats | null;
  bowler: BowlerLiveStats;
  recent_balls: RecentBall[];
  match_status: string;
  is_key_moment?: boolean;
  key_moment_info?: KeyMoment | null;
  delivery_event: Delivery;
}

export type ScoreboardState = SnapshotState;

export interface PlayerInfo {
  name: string;
  team: string;
  role: string;
  credits: number;
}

export interface MatchMetadata {
  match_id: string;
  event_name: string;
  venue: string;
  city?: string;
  dates: string[];
  teams: string[];
  toss: {
    winner: string;
    decision: string;
  };
  outcome: {
    winner?: string;
    by?: Record<string, any>;
    result?: string;
  };
  total_deliveries: number;
  players: Record<string, string[]>;
  roster: PlayerInfo[];
  source_attribution: string;
}

export interface RulesetConfig {
  ruleset_id: string;
  ruleset_name: string;
  format?: string;
  source_url: string;
  version: string;
  last_verified: string;
  retrospective_disclosure?: string;
  run: number;
  boundary_four_bonus: number;
  six_bonus: number;
  twenty_five_run_bonus: number;
  half_century_bonus: number;
  seventy_five_run_bonus: number;
  century_bonus: number;
  duck_penalty: number;
  wicket_normal: number;
  lbw_bowled_bonus: number;
  dot_ball_bowled: number;
  three_wicket_bonus: number;
  four_wicket_bonus: number;
  five_wicket_bonus: number;
  maiden_over: number;
  catch: number;
  three_catch_bonus: number;
  stumping: number;
  run_out_direct: number;
  run_out_shared: number;
  starting_xi: number;
  captain_multiplier: number;
  vice_captain_multiplier: number;
}

export interface BreakdownItem {
  category: string;
  label: string;
  count: number;
  points_each: number;
  total_points: number;
}

export interface PlayerFantasyScore {
  player_name: string;
  team: string;
  role: string;
  is_captain: boolean;
  is_vice_captain: boolean;
  multiplier: number;
  raw_points: number;
  total_points: number;
  breakdown: BreakdownItem[];
  recent_delta: number;
}

export interface PlayerDelta {
  player_name: string;
  team: string;
  reason: string;
  category: string;
  raw_delta: number;
  multiplier: number;
  net_delta: number;
  previous_total: number;
  new_total: number;
  is_captain: boolean;
  is_vice_captain: boolean;
}

export interface BallFantasyImpact {
  delivery_index: number;
  over_display: string;
  player_deltas: PlayerDelta[];
  fantasy_team_total: number;
  fantasy_team_delta: number;
  summary_sentence: string;
}

export interface FantasyTeamConfig {
  selected_players: string[];
  captain: string;
  vice_captain: string;
}

export interface OptimalCaptaincyComparison {
  current_captain: string;
  current_vice_captain: string;
  current_combo_points: number;
  optimal_captain: string;
  optimal_vice_captain: string;
  optimal_combo_points: number;
  optimal_team_total: number;
  point_difference: number;
  is_already_optimal: boolean;
  summary: string;
}

export interface FantasyScoreResponse {
  delivery_index: number;
  over_display: string;
  player_scores: Record<string, PlayerFantasyScore>;
  ball_delta: BallFantasyImpact;
  team_total: number;
  team_delta: number;
  optimal_captaincy?: OptimalCaptaincyComparison | null;
}

export interface EvidenceBoundary {
  grounded_in_data: string[];
  unavailable_evidence: string[];
}

export interface RuleExplanation {
  law_name: string;
  law_number?: string;
  summary: string;
}

export interface EventExplanation {
  delivery_index: number;
  over_display: string;
  headline: string;
  what_happened: string;
  simple_cricket_explanation: string;
  why_it_matters: string;
  fantasy_impact_explanation: string;
  cricket_rule: RuleExplanation;
  evidence: EvidenceBoundary;
  data_limitations: string[];
  next_ball_watchout?: string;
  fan_takeaway: string;
  engine_source: 'gemini_ai' | 'deterministic_rules_engine';
}
