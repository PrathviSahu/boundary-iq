import React from 'react';
import { X, ExternalLink, ShieldCheck, Award, Zap, AlertCircle } from 'lucide-react';
import { RulesetConfig } from '../types';

interface RulesModalProps {
  isOpen: boolean;
  onClose: () => void;
  ruleset: RulesetConfig | null;
}

export const RulesModal: React.FC<RulesModalProps> = ({ isOpen, onClose, ruleset }) => {
  if (!isOpen || !ruleset) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-3xl bg-white border border-ink-border rounded-lg shadow-xl overflow-hidden my-6 max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-border bg-white">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-md bg-forest-50 border border-forest-200 text-forest-700">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-ink-primary tracking-tight">{ruleset.ruleset_name}</h2>
              <div className="flex items-center space-x-2 text-xs text-ink-secondary mt-0.5">
                <span className="px-1.5 py-0.2 rounded bg-forest-100 text-forest-800 font-mono font-medium">
                  v{ruleset.version}
                </span>
                <span>•</span>
                <span>Format: {ruleset.format}</span>
                <span>•</span>
                <span>Verified: {ruleset.last_verified}</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-ink-secondary hover:text-ink-primary hover:bg-canvas transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs text-ink-primary bg-canvas">
          {/* Retrospective Application Notice */}
          <div className="flex items-start space-x-3 p-3.5 rounded-md bg-forest-50 border border-forest-200 text-forest-900">
            <ShieldCheck className="w-4 h-4 text-forest-700 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-semibold text-forest-800 text-xs">Standard T20 Ruleset — Retrospective Application</p>
              <p className="text-[11px] text-ink-secondary leading-relaxed">
                {ruleset.retrospective_disclosure ||
                  "Standard Dream11 T20 scoring rules applied retrospectively to the ICC Men's T20 World Cup 2024 Final for analytics and demonstration."}
              </p>
              <a
                href={ruleset.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-1 text-[11px] text-forest-700 hover:text-forest-800 font-medium underline"
              >
                <span>View Official Dream11 Standard T20 Point System</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          {/* Scoring Tables Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Batting */}
            <div className="bg-white border border-ink-border rounded-md p-3.5 space-y-2">
              <h3 className="text-xs font-bold text-ink-primary flex items-center space-x-1.5 pb-1 border-b border-ink-border">
                <Zap className="w-3.5 h-3.5 text-forest-600" />
                <span>Batting Points (Standard T20)</span>
              </h3>
              <div className="space-y-1.5 text-xs text-ink-secondary">
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Each Run Scored</span>
                  <span className="font-mono text-ink-primary font-semibold tabular-nums">+{ruleset.run} pt</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Boundary Four (4) Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.boundary_four_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Boundary Six (6) Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.six_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>25-Run Milestone Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.twenty_five_run_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Half-Century Bonus (50+ runs)</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.half_century_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>75-Run Milestone Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.seventy_five_run_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Century Bonus (100+ runs)</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.century_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span>Dismissal for Duck (BAT/WK/AR)</span>
                  <span className="font-mono text-sport-wicket font-semibold tabular-nums">{ruleset.duck_penalty} pts</span>
                </div>
              </div>
            </div>

            {/* Bowling */}
            <div className="bg-white border border-ink-border rounded-md p-3.5 space-y-2">
              <h3 className="text-xs font-bold text-ink-primary flex items-center space-x-1.5 pb-1 border-b border-ink-border">
                <Zap className="w-3.5 h-3.5 text-forest-600" />
                <span>Bowling Points (Standard T20)</span>
              </h3>
              <div className="space-y-1.5 text-xs text-ink-secondary">
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Wicket (excluding Run Out)</span>
                  <span className="font-mono text-ink-primary font-semibold tabular-nums">+{ruleset.wicket_normal} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Bowled / LBW Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.lbw_bowled_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Dot Ball Bowled</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.dot_ball_bowled} pt</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>3-Wicket Haul Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.three_wicket_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>4-Wicket Haul Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.four_wicket_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>5-Wicket Haul Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.five_wicket_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span>Maiden Over Completed</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.maiden_over} pts</span>
                </div>
              </div>
            </div>

            {/* Fielding */}
            <div className="bg-white border border-ink-border rounded-md p-3.5 space-y-2">
              <h3 className="text-xs font-bold text-ink-primary flex items-center space-x-1.5 pb-1 border-b border-ink-border">
                <Zap className="w-3.5 h-3.5 text-forest-600" />
                <span>Fielding Points</span>
              </h3>
              <div className="space-y-1.5 text-xs text-ink-secondary">
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Catch Taken</span>
                  <span className="font-mono text-ink-primary font-semibold tabular-nums">+{ruleset.catch} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>3 Catch Bonus</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.three_catch_bonus} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Stumping</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.stumping} pts</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Run Out (Direct Hit)</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.run_out_direct} pts</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span>Run Out (Shared / Other)</span>
                  <span className="font-mono text-forest-700 font-semibold tabular-nums">+{ruleset.run_out_shared} pts</span>
                </div>
              </div>
            </div>

            {/* Multipliers & Lineup */}
            <div className="bg-white border border-ink-border rounded-md p-3.5 space-y-2">
              <h3 className="text-xs font-bold text-ink-primary flex items-center space-x-1.5 pb-1 border-b border-ink-border">
                <Award className="w-3.5 h-3.5 text-forest-600" />
                <span>Multipliers & Lineup</span>
              </h3>
              <div className="space-y-1.5 text-xs text-ink-secondary">
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Captain Multiplier (C)</span>
                  <span className="font-mono text-forest-700 font-bold tabular-nums">{ruleset.captain_multiplier}x Points</span>
                </div>
                <div className="flex justify-between py-0.5 border-b border-ink-border">
                  <span>Vice-Captain Multiplier (VC)</span>
                  <span className="font-mono text-ink-primary font-bold tabular-nums">{ruleset.vice_captain_multiplier}x Points</span>
                </div>
                <div className="flex justify-between py-0.5">
                  <span>Announced Starting Lineup</span>
                  <span className="font-mono text-ink-primary font-semibold tabular-nums">+{ruleset.starting_xi} pts</span>
                </div>
              </div>
            </div>
          </div>

          {/* Legal Disclaimer */}
          <div className="p-3 rounded-md bg-white border border-ink-border text-[11px] text-ink-secondary space-y-1">
            <div className="flex items-center space-x-1.5 font-semibold text-ink-primary">
              <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
              <span>Attribution & Scope Disclosure</span>
            </div>
            <p>
              BoundaryIQ is an independent research and sports analytics application. It is not affiliated with, endorsed by, or sponsored by Dream11, Sporta Technologies, the BCCI, or the ICC.
            </p>
            <p>
              Cricsheet ball-by-ball source data records match events reliably, but does not include Hawkeye ball tracking coordinates or speed telemetry. BoundaryIQ strictly preserves these evidence boundaries.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-ink-border bg-white flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-md bg-forest-600 hover:bg-forest-700 text-white font-semibold text-xs transition-colors shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
