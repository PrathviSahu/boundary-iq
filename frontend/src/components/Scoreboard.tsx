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
        {/* Main Team Score */}
        <div className="md:col-span-12 lg:col-span-4 bg-canvas/70 border border-ink-border rounded-md p-3 flex items-center space-x-3.5 min-w-0">
          <div className="w-12 h-12 rounded-lg bg-forest-50 border border-forest-200 flex items-center justify-center font-bold text-sm text-forest-800 tracking-wider shrink-0">
            {scoreboard.batting_team === 'India' ? 'IND' : 'SA'}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline space-x-2 flex-wrap">
              <span className="text-3xl sm:text-4xl font-extrabold text-ink-primary tracking-tight font-mono tabular-nums">
                {scoreboard.team_score}
                <span className="text-ink-secondary font-normal text-2xl">/{scoreboard.team_wickets}</span>
              </span>
              <span className="text-sm font-mono text-ink-secondary font-medium">
                ({scoreboard.overs_display} ov)
              </span>
            </div>
            <div className="text-xs text-ink-secondary mt-0.5 truncate">
              <span className="font-medium text-ink-primary">{scoreboard.batting_team}</span>
              <span className="text-ink-muted mx-1.5">vs</span>
              <span>{scoreboard.bowling_team}</span>
            </div>
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
