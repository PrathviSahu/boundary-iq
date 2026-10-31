import React from 'react';
import { ScoreboardState, Delivery } from '../types';
import { Target } from 'lucide-react';

interface ScoreboardProps {
  scoreboard: ScoreboardState | null;
  currentDelivery: Delivery | null;
  onSelectBall: (index: number) => void;
}

export const Scoreboard: React.FC<ScoreboardProps> = ({
  scoreboard,
  currentDelivery,
  onSelectBall,
}) => {
  if (!scoreboard || !currentDelivery) {
    return (
      <div className="bg-surface border border-ink-border rounded-lg p-5 animate-pulse">
        <div className="h-20 bg-forest-50/50 rounded" />
      </div>
    );
  }

  const isChase = scoreboard.innings === 2;
  const team1Name = scoreboard.innings === 1 ? scoreboard.batting_team : (scoreboard.first_innings_team || scoreboard.bowling_team);
  const team2Name = scoreboard.innings === 1 ? scoreboard.bowling_team : scoreboard.batting_team;
  const team1Code = team1Name.toLowerCase().includes('india') ? 'IND' : team1Name.slice(0, 3).toUpperCase();
  const team2Code = team2Name.toLowerCase().includes('south africa') ? 'SA' : team2Name.slice(0, 3).toUpperCase();

  const inn1Score = scoreboard.innings === 1 ? scoreboard.team_score : (scoreboard.first_innings_score ?? 176);
  const inn1Wickets = scoreboard.innings === 1 ? scoreboard.team_wickets : (scoreboard.first_innings_wickets ?? 7);
  const inn1Overs = scoreboard.innings === 1 ? scoreboard.overs_display : (scoreboard.first_innings_overs ?? '20.0');

  return (
    <div className="bg-surface border border-ink-border rounded-lg shadow-sm p-3.5 sm:p-5 space-y-3.5 min-w-0">
      {/* Top Equation & Status Header */}
      <div className="flex flex-wrap items-center justify-between pb-2.5 border-b border-ink-border text-xs gap-2">
        <div className="flex items-center space-x-2 flex-wrap gap-y-1 min-w-0">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-forest-100 text-forest-800 uppercase tracking-wide shrink-0">
            Innings {scoreboard.innings}
          </span>
          <span className="font-medium text-ink-primary break-words">
            {scoreboard.match_status}
          </span>
        </div>

        <div className="flex items-center space-x-2.5 sm:space-x-4 font-mono text-xs shrink-0">
          <div className="flex items-center space-x-1 text-ink-secondary">
            <span>CRR:</span>
            <span className="font-bold text-ink-primary tabular-nums">{scoreboard.run_rate}</span>
          </div>
          {isChase && scoreboard.required_run_rate !== null && (
            <div className="flex items-center space-x-1 text-ink-secondary">
              <Target className="w-3.5 h-3.5 text-forest-600" />
              <span>RRR:</span>
              <span className="font-bold text-forest-700 tabular-nums">{scoreboard.required_run_rate}</span>
            </div>
          )}
          {isChase && scoreboard.target && (
            <div className="flex items-center space-x-1 text-ink-secondary">
              <span>Target:</span>
              <span className="font-bold text-ink-primary tabular-nums">{scoreboard.target}</span>
            </div>
          )}
        </div>
      </div>

      {/* Primary Scorecard Grid: Team Score | Batting Table | Bowling Table */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 sm:gap-3.5 lg:gap-4 items-stretch">
        {/* Main Team Score: Both Teams Match Scoreboard */}
        <div className="md:col-span-12 lg:col-span-4 bg-canvas/70 border border-ink-border rounded-md p-2.5 sm:p-3 flex flex-col justify-between space-y-2 min-w-0">
          {/* Team 1: India */}
          <div
            className={`p-2 rounded-md border transition-all ${
              scoreboard.innings === 1
                ? 'bg-white border-forest-300 shadow-xs ring-1 ring-forest-500/20'
                : 'bg-canvas/60 border-ink-border/70'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center space-x-2 min-w-0">
                <span className="w-8 h-8 rounded bg-forest-50 border border-forest-200 flex items-center justify-center font-bold text-xs text-forest-800 tracking-wider shrink-0">
                  {team1Code}
                </span>
                <div className="min-w-0">
                  <div className="flex items-center space-x-1.5">
                    <span className="font-semibold text-xs text-ink-primary truncate">{team1Name}</span>
                    {scoreboard.innings === 1 ? (
                      <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[9px] font-bold bg-forest-100 text-forest-800 uppercase tracking-wider shrink-0">
                        <span className="w-1.5 h-1.5 rounded-full bg-forest-600 mr-1 animate-pulse" />
                        Batting
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-medium bg-canvas text-ink-secondary border border-ink-border shrink-0">
                        1st Innings
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Score */}
              <div className="text-right shrink-0 font-mono tabular-nums">
                <span className={`text-base sm:text-lg font-extrabold ${scoreboard.innings === 1 ? 'text-forest-700' : 'text-ink-primary'}`}>
                  {inn1Score}
                </span>
                <span className="text-ink-secondary text-sm font-normal">/{inn1Wickets}</span>
                <span className="text-[11px] text-ink-muted font-normal ml-1">
                  ({inn1Overs} ov)
                </span>
              </div>
            </div>
          </div>

          {/* Team 2: South Africa */}
          <div
            className={`p-2 rounded-md border transition-all ${
              scoreboard.innings === 2
                ? 'bg-white border-forest-300 shadow-xs ring-1 ring-forest-500/20'
                : 'bg-canvas/40 border-ink-border/50'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center space-x-2 min-w-0">
                <span className="w-8 h-8 rounded bg-forest-50 border border-forest-200 flex items-center justify-center font-bold text-xs text-forest-800 tracking-wider shrink-0">
                  {team2Code}
                </span>
                <div className="min-w-0">
                  <div className="flex items-center space-x-1.5">
                    <span className="font-semibold text-xs text-ink-primary truncate">{team2Name}</span>
                    {scoreboard.innings === 2 ? (
                      <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[9px] font-bold bg-forest-100 text-forest-800 uppercase tracking-wider shrink-0">
                        <span className="w-1.5 h-1.5 rounded-full bg-forest-600 mr-1 animate-pulse" />
                        Chasing
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-medium text-ink-muted">
                        Yet to bat
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Score */}
              <div className="text-right shrink-0">
                {scoreboard.innings === 2 ? (
                  <div className="font-mono tabular-nums">
                    <span className="text-base sm:text-lg font-extrabold text-forest-700">
                      {scoreboard.team_score}
                    </span>
                    <span className="text-ink-secondary text-sm font-normal">/{scoreboard.team_wickets}</span>
                    <span className="text-[11px] text-ink-muted font-normal ml-1">
                      ({scoreboard.overs_display} ov)
                    </span>
                  </div>
                ) : (
                  <span className="text-xs font-mono text-ink-muted italic">Yet to bat</span>
                )}
              </div>
            </div>

            {/* Chase Equation for Innings 2 */}
            {scoreboard.innings === 2 && scoreboard.runs_needed !== null && scoreboard.runs_needed !== undefined && (
              <div className="mt-1 pt-1 border-t border-ink-border/40 flex items-center justify-between text-[10px] text-ink-secondary font-mono">
                <span>Target: <strong className="text-ink-primary font-bold">{scoreboard.target ?? 177}</strong></span>
                <span className="text-forest-700 font-semibold truncate ml-1">
                  {scoreboard.runs_needed > 0
                    ? `Need ${scoreboard.runs_needed} off ${scoreboard.balls_remaining}b`
                    : 'Target Achieved!'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Current Batters Table */}
        <div className="md:col-span-6 lg:col-span-4 bg-canvas border border-ink-border rounded-md p-3 space-y-2 text-xs min-w-0">
          <div className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wider flex items-center justify-between pb-1 border-b border-ink-border">
            <span>Batting</span>
            <span className="font-mono text-ink-muted">R (B) • 4s • 6s • SR</span>
          </div>

          {/* Striker */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-1.5 border-b border-ink-border/50 sm:border-0 sm:pb-0">
            <div className="flex items-center space-x-1.5 min-w-0">
              <span className="text-forest-600 font-bold shrink-0">*</span>
              <span className="text-ink-primary font-semibold truncate text-xs">{scoreboard.striker.name}</span>
            </div>
            <div className="flex items-center justify-between sm:justify-end space-x-1.5 font-mono text-[11px] tabular-nums text-ink-secondary pl-3 sm:pl-0 shrink-0">
              <span className="font-bold text-ink-primary">
                {scoreboard.striker.runs}
                <span className="text-ink-muted font-normal text-[10px]"> ({scoreboard.striker.balls})</span>
              </span>
              <span className="text-ink-muted">•</span>
              <span>{scoreboard.striker.fours}×4</span>
              <span className="text-ink-muted">•</span>
              <span>{scoreboard.striker.sixes}×6</span>
              <span className="text-ink-muted">•</span>
              <span className="text-forest-700 font-semibold">{scoreboard.striker.strike_rate}</span>
            </div>
          </div>

          {/* Non Striker */}
          {scoreboard.non_striker && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <div className="flex items-center space-x-1.5 min-w-0 pl-3 sm:pl-0">
                <span className="text-ink-primary font-medium truncate text-xs">{scoreboard.non_striker.name}</span>
              </div>
              <div className="flex items-center justify-between sm:justify-end space-x-1.5 font-mono text-[11px] tabular-nums text-ink-secondary pl-3 sm:pl-0 shrink-0">
                <span className="text-ink-primary font-medium">
                  {scoreboard.non_striker.runs}
                  <span className="text-ink-muted font-normal text-[10px]"> ({scoreboard.non_striker.balls})</span>
                </span>
                <span className="text-ink-muted">•</span>
                <span>{scoreboard.non_striker.fours}×4</span>
                <span className="text-ink-muted">•</span>
                <span>{scoreboard.non_striker.sixes}×6</span>
                <span className="text-ink-muted">•</span>
                <span>{scoreboard.non_striker.strike_rate}</span>
              </div>
            </div>
          )}
        </div>

        {/* Current Bowler Table */}
        <div className="md:col-span-6 lg:col-span-4 bg-canvas border border-ink-border rounded-md p-3 space-y-2 text-xs min-w-0">
          <div className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wider flex items-center justify-between pb-1 border-b border-ink-border">
            <span>Bowling</span>
            <span className="font-mono text-ink-muted">O • M • R • W • ECO</span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
            <span className="font-semibold text-ink-primary truncate text-xs min-w-0">
              {scoreboard.bowler.name}
            </span>
            <div className="flex items-center justify-between sm:justify-end space-x-1.5 font-mono text-ink-secondary text-[11px] tabular-nums shrink-0">
              <span>{scoreboard.bowler.overs} ov</span>
              <span className="text-ink-muted">•</span>
              <span>{scoreboard.bowler.maidens} M</span>
              <span className="text-ink-muted">•</span>
              <span className="font-bold text-ink-primary">{scoreboard.bowler.wickets}/{scoreboard.bowler.runs_conceded}</span>
              <span className="text-ink-muted">•</span>
              <span className="text-forest-700 font-semibold">Eco {scoreboard.bowler.economy}</span>
            </div>
          </div>

          <div className="text-[10px] text-ink-secondary font-mono flex items-center justify-between pt-1 border-t border-ink-border/50">
            <span>Spell:</span>
            <span className="font-medium text-ink-primary">
              {scoreboard.bowler.wickets}/{scoreboard.bowler.runs_conceded} in {scoreboard.bowler.overs} ov
            </span>
          </div>
        </div>
      </div>

      {/* Recent Deliveries Strip */}
      <div className="pt-2.5 border-t border-ink-border flex items-center space-x-2 overflow-x-auto max-w-full">
        <span className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wider whitespace-nowrap mr-1">
          Recent Balls:
        </span>
        <div className="flex items-center space-x-1.5 py-0.5">
          {scoreboard.recent_balls.map((b) => {
            const isSelected = b.index === currentDelivery.index;
            let badgeStyle = 'bg-canvas text-ink-primary border-ink-border hover:bg-forest-50';
            let label = b.total_runs.toString();

            if (b.is_wicket) {
              badgeStyle = 'bg-sport-wicketBg text-sport-wicket border-sport-wicketBorder font-bold';
              label = 'W';
            } else if (b.is_six) {
              badgeStyle = 'bg-forest-100 text-forest-800 border-forest-300 font-bold';
              label = '6';
            } else if (b.is_four) {
              badgeStyle = 'bg-forest-50 text-forest-700 border-forest-200 font-bold';
              label = '4';
            } else if (b.extra_type) {
              badgeStyle = 'bg-amber-50 text-amber-800 border-amber-200 font-mono text-[10px]';
              label = b.extra_type === 'wides' ? `${b.total_runs}wd` : `${b.total_runs}nb`;
            } else if (b.total_runs === 0) {
              label = '•';
            }

            return (
              <button
                key={b.index}
                onClick={() => onSelectBall(b.index)}
                className={`w-7 h-7 rounded text-xs font-mono flex items-center justify-center border transition-all ${badgeStyle} ${
                  isSelected
                    ? 'ring-2 ring-forest-600 ring-offset-1 font-bold'
                    : ''
                }`}
                title={`Over ${b.over_display}: ${label}`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
