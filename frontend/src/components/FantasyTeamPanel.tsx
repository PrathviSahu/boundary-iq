import React, { useState } from 'react';
import { ChevronDown, ChevronUp, SlidersHorizontal } from 'lucide-react';
import { PlayerFantasyScore, BallFantasyImpact, FantasyTeamConfig } from '../types';

interface FantasyTeamPanelProps {
  playerScores: Record<string, PlayerFantasyScore>;
  teamTotal: number;
  teamDelta: number;
  currentDeltaImpact?: BallFantasyImpact | null;
  teamConfig: FantasyTeamConfig;
  onOpenCustomizer: () => void;
  onSelectPreset: (presetName: string) => void;
}

export const FantasyTeamPanel: React.FC<FantasyTeamPanelProps> = ({
  playerScores,
  teamTotal,
  teamDelta,
  teamConfig,
  onOpenCustomizer,
  onSelectPreset,
}) => {
  const [expandedPlayer, setExpandedPlayer] = useState<string | null>(null);

  const toggleExpand = (name: string) => {
    setExpandedPlayer(expandedPlayer === name ? null : name);
  };

  const selectedList = teamConfig.selected_players;

  return (
    <div className="bg-surface border border-ink-border rounded-lg p-4 shadow-sm flex flex-col h-full space-y-3.5">
      {/* Top Banner: Total Fantasy Points & Ball Delta */}
      <div className="p-3 sm:p-3.5 rounded-md bg-canvas border border-ink-border min-w-0">
        <div className="flex items-center justify-between mb-1.5 text-xs">
          <span className="font-semibold text-ink-secondary uppercase tracking-wider text-[10px]">
            User Fantasy Squad
          </span>
          <span className="font-mono text-[10px] font-semibold text-forest-700 bg-forest-100 px-1.5 py-0.5 rounded">
            {selectedList.length}/11 Players
          </span>
        </div>

        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div className="min-w-0">
            <div className="text-3xl font-extrabold text-ink-primary font-mono tracking-tight tabular-nums">
              {teamTotal}
              <span className="text-xs font-normal text-ink-secondary ml-1 font-sans">pts</span>
            </div>
            <p className="text-[11px] text-ink-secondary">Total Squad Points</p>
          </div>

          {/* Current Ball Delta */}
          <div className="text-left sm:text-right shrink-0">
            <div
              className={`text-xs font-mono font-bold px-2 py-0.5 rounded border tabular-nums inline-block ${
                teamDelta > 0
                  ? 'bg-forest-100 text-forest-800 border-forest-300'
                  : teamDelta < 0
                  ? 'bg-sport-wicketBg text-sport-wicket border-sport-wicketBorder'
                  : 'bg-white text-ink-secondary border-ink-border'
              }`}
            >
              {teamDelta > 0 ? `+${teamDelta}` : teamDelta} pts
            </div>
            <p className="text-[10px] text-ink-muted mt-0.5">This delivery</p>
          </div>
        </div>
      </div>

      {/* Captain & Vice-Captain Key Summary */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        {/* Captain */}
        <div className="p-2 rounded-md bg-white border border-forest-200">
          <div className="flex items-center justify-between text-[10px] mb-0.5">
            <span className="text-ink-secondary font-medium">Captain</span>
            <span className="font-mono font-bold text-forest-700 bg-forest-100 px-1 rounded">2x</span>
          </div>
          <div className="font-semibold text-ink-primary truncate text-[11px]">
            {teamConfig.captain}
          </div>
          <div className="font-mono text-xs font-bold text-forest-700 tabular-nums mt-0.5">
            {playerScores[teamConfig.captain]?.total_points ?? 0} pts
          </div>
        </div>

        {/* Vice-Captain */}
        <div className="p-2 rounded-md bg-white border border-ink-border">
          <div className="flex items-center justify-between text-[10px] mb-0.5">
            <span className="text-ink-secondary font-medium">Vice-Captain</span>
            <span className="font-mono font-bold text-ink-primary bg-canvas px-1 rounded border border-ink-border">1.5x</span>
          </div>
          <div className="font-semibold text-ink-primary truncate text-[11px]">
            {teamConfig.vice_captain}
          </div>
          <div className="font-mono text-xs font-bold text-ink-primary tabular-nums mt-0.5">
            {playerScores[teamConfig.vice_captain]?.total_points ?? 0} pts
          </div>
        </div>
      </div>

      {/* Squad Actions: Customise & Quick Presets */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-ink-border text-xs min-w-0">
        <button
          onClick={onOpenCustomizer}
          className="py-1 px-2.5 rounded-md bg-forest-600 hover:bg-forest-700 text-white font-medium transition-colors flex items-center space-x-1 shadow-xs shrink-0"
        >
          <SlidersHorizontal className="w-3 h-3" />
          <span>Customise XI</span>
        </button>

        <div className="flex items-center space-x-1 flex-wrap gap-y-1">
          <button
            onClick={() => onSelectPreset('balanced')}
            className="px-2 py-0.5 sm:py-1 rounded bg-canvas hover:bg-forest-50 text-[10px] text-ink-secondary hover:text-ink-primary font-medium border border-ink-border transition-colors"
            title="Balanced XI (IND 6 / SA 5)"
          >
            Balanced
          </button>
          <button
            onClick={() => onSelectPreset('india_heavy')}
            className="px-2 py-0.5 sm:py-1 rounded bg-canvas hover:bg-forest-50 text-[10px] text-ink-secondary hover:text-ink-primary font-medium border border-ink-border transition-colors"
            title="India Heavy XI (IND 7 / SA 4)"
          >
            IND+
          </button>
          <button
            onClick={() => onSelectPreset('sa_heavy')}
            className="px-2 py-0.5 sm:py-1 rounded bg-canvas hover:bg-forest-50 text-[10px] text-ink-secondary hover:text-ink-primary font-medium border border-ink-border transition-colors"
            title="South Africa Heavy XI"
          >
            SA+
          </button>
        </div>
      </div>

      {/* Selected Players Table / List */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5 min-w-0">
        <div className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wider px-0.5">
          Squad Roster (11):
        </div>

        {selectedList.map((pName) => {
          const score = playerScores[pName];
          if (!score) return null;

          const isC = teamConfig.captain === pName;
          const isVC = teamConfig.vice_captain === pName;
          const isExpanded = expandedPlayer === pName;

          return (
            <div
              key={pName}
              className="bg-white border border-ink-border rounded-md overflow-hidden transition-colors hover:border-forest-300 min-w-0"
            >
              <div
                onClick={() => toggleExpand(pName)}
                className="p-2 flex items-center justify-between cursor-pointer select-none text-xs gap-1.5 min-w-0"
              >
                <div className="flex items-center space-x-2 min-w-0">
                  <span
                    className={`text-[9px] font-mono px-1 py-0.2 rounded font-semibold shrink-0 ${
                      score.team === 'India'
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'bg-forest-50 text-forest-700 border border-forest-200'
                    }`}
                  >
                    {score.team === 'India' ? 'IND' : 'SA'}
                  </span>

                  <div className="min-w-0">
                    <div className="flex items-center space-x-1.5">
                      <span className="font-semibold text-ink-primary text-xs truncate max-w-[110px] sm:max-w-none">{pName}</span>
                      {isC && (
                        <span className="text-[9px] font-mono font-bold bg-forest-600 text-white px-1 rounded shrink-0">
                          C
                        </span>
                      )}
                      {isVC && (
                        <span className="text-[9px] font-mono font-bold bg-ink-primary text-white px-1 rounded shrink-0">
                          VC
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-ink-secondary font-mono">{score.role}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
                  <div className="text-right">
                    <span className="text-xs font-bold text-ink-primary font-mono tabular-nums">
                      {score.total_points}
                    </span>
                    <span className="text-[10px] text-ink-muted block font-mono">
                      {score.multiplier > 1.0 ? `${score.raw_points} × ${score.multiplier}` : 'pts'}
                    </span>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-3.5 h-3.5 text-ink-muted shrink-0" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5 text-ink-muted shrink-0" />
                  )}
                </div>
              </div>

              {/* Expandable Breakdown Drawer */}
              {isExpanded && (
                <div className="p-2.5 bg-canvas border-t border-ink-border text-xs space-y-1">
                  <div className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wider mb-1 flex items-center justify-between pb-1 border-b border-ink-border">
                    <span>Scoring Component Breakdown</span>
                    <span>Pts</span>
                  </div>
                  {score.breakdown.map((item, idx) => (
                    <div key={idx} className="flex justify-between text-ink-secondary text-[11px]">
                      <span>{item.label}</span>
                      <span className="font-mono text-forest-700 font-semibold tabular-nums">
                        +{item.total_points}
                      </span>
                    </div>
                  ))}
                  <div className="pt-1 border-t border-ink-border flex justify-between font-semibold text-[11px]">
                    <span className="text-ink-secondary">Base Raw Total</span>
                    <span className="font-mono text-ink-primary tabular-nums">{score.raw_points}</span>
                  </div>
                  {score.multiplier > 1.0 && (
                    <div className="flex justify-between font-semibold text-[11px] text-forest-700">
                      <span>Multiplier ({isC ? 'Captain 2x' : 'Vice-Captain 1.5x'})</span>
                      <span className="font-mono tabular-nums">{score.total_points} pts</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
