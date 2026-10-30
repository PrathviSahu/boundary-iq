import {
  MatchMetadata,
  RulesetConfig,
  Delivery,
  SnapshotState,
  KeyMoment,
  PlayerInfo,
  FantasyTeamConfig,
  FantasyScoreResponse,
  EventExplanation,
} from '../types';

// In production on Vercel, requests point to the deployed Render backend via VITE_API_BASE_URL.
// In local development without VITE_API_BASE_URL, defaults to '/api' handled by Vite proxy.
const getApiBase = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (!envUrl || typeof envUrl !== 'string' || envUrl.trim() === '') {
    return '/api';
  }
  const cleanUrl = envUrl.trim().replace(/\/+$/, '');
  return cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
};

const API_BASE = getApiBase();

export async function fetchHealth(): Promise<{
  status: string;
  gemini_ai_enabled: boolean;
  gemini_model: string;
  match_id: string;
  match_name: string;
  total_deliveries: number;
}> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchMatches(): Promise<MatchMetadata[]> {
  const res = await fetch(`${API_BASE}/matches`);
  if (!res.ok) throw new Error('Failed to fetch matches');
  return res.json();
}

export async function fetchMatch(matchId: string): Promise<MatchMetadata> {
  const res = await fetch(`${API_BASE}/matches/${matchId}`);
  if (!res.ok) throw new Error(`Failed to fetch match ${matchId}`);
  return res.json();
}

export async function fetchDeliveries(matchId: string): Promise<Delivery[]> {
  const res = await fetch(`${API_BASE}/matches/${matchId}/deliveries`);
  if (!res.ok) throw new Error('Failed to fetch deliveries');
  return res.json();
}

export async function fetchSnapshot(matchId: string, index: number): Promise<SnapshotState> {
  const res = await fetch(`${API_BASE}/matches/${matchId}/snapshot/${index}`);
  if (!res.ok) throw new Error(`Failed to fetch snapshot at ${index}`);
  return res.json();
}

export async function fetchKeyMoments(matchId: string, category?: string): Promise<KeyMoment[]> {
  const url = category && category !== 'all'
    ? `${API_BASE}/matches/${matchId}/key-moments?category=${encodeURIComponent(category)}`
    : `${API_BASE}/matches/${matchId}/key-moments`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch key moments');
  return res.json();
}

export async function fetchPlayers(matchId: string): Promise<PlayerInfo[]> {
  const res = await fetch(`${API_BASE}/matches/${matchId}/players`);
  if (!res.ok) throw new Error('Failed to fetch players');
  return res.json();
}

export async function fetchRuleset(matchId: string): Promise<RulesetConfig> {
  const res = await fetch(`${API_BASE}/matches/${matchId}/ruleset`);
  if (!res.ok) throw new Error('Failed to fetch scoring ruleset');
  return res.json();
}

export async function computeCustomScores(
  deliveryIndex: number,
  teamConfig?: FantasyTeamConfig
): Promise<FantasyScoreResponse> {
  const res = await fetch(`${API_BASE}/fantasy/scores/${deliveryIndex}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: teamConfig ? JSON.stringify(teamConfig) : undefined,
  });
  if (!res.ok) throw new Error(`Failed to compute scores at ${deliveryIndex}`);
  return res.json();
}

export async function explainDelivery(
  matchId: string,
  deliveryIndex: number,
  teamConfig?: FantasyTeamConfig,
  signal?: AbortSignal
): Promise<EventExplanation> {
  const res = await fetch(`${API_BASE}/matches/${matchId}/explain/${deliveryIndex}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: teamConfig ? JSON.stringify(teamConfig) : undefined,
    signal,
  });
  if (!res.ok) throw new Error(`Failed to explain delivery ${deliveryIndex}`);
  return res.json();
}
