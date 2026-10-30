import React from 'react';
import { Award, ShieldCheck, Sparkles } from 'lucide-react';
import { MatchMetadata, RulesetConfig } from '../types';

interface HeaderProps {
  metadata: MatchMetadata | null;
  ruleset: RulesetConfig | null;
  geminiActive: boolean;
  onOpenRules: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  metadata,
  ruleset,
  geminiActive,
  onOpenRules,
}) => {
  return (
    <header className="border-b border-ink-border bg-surface sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-2 sm:gap-3">
        {/* Brand & Wordmark */}
        <div className="flex items-center space-x-2 shrink-0 min-w-0">
          <div className="w-7 h-7 rounded-md bg-forest-600 flex items-center justify-center text-white font-black text-xs tracking-tighter shrink-0">
            BIQ
          </div>
          <div className="flex items-baseline space-x-1.5 sm:space-x-2">
            <h1 className="text-base font-bold tracking-tight text-ink-primary m-0 inline-block">
              Boundary<span className="text-forest-600">IQ</span>
            </h1>
            <span className="hidden xl:inline-block text-[11px] font-medium text-ink-secondary tracking-normal">
              Sports Analytics & Match Companion
            </span>
          </div>
        </div>

        {/* Responsive Match Context Center Pill / Breadcrumbs */}
        <nav aria-label="Breadcrumb" className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-md bg-forest-50 border border-forest-200/60 text-xs text-ink-secondary shrink truncate">
          <span className="font-semibold text-ink-primary shrink-0">
            {metadata ? `${metadata.teams[0]} vs ${metadata.teams[1]}` : 'IND vs SA'}
          </span>
          <span className="text-ink-muted shrink-0" aria-hidden="true">•</span>
          <span className="hidden lg:inline truncate">
            {metadata?.venue ? metadata.venue.split(',')[0] : 'Kensington Oval'}
          </span>
          <span className="hidden lg:inline text-ink-muted shrink-0" aria-hidden="true">•</span>
          <span className="text-forest-700 font-medium shrink-0">T20 World Cup Final</span>
        </nav>

        {/* Engine Status & Ruleset Trigger */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
          {/* Ruleset Pill */}
          <button
            onClick={onOpenRules}
            className="flex items-center space-x-1 sm:space-x-1.5 px-2 sm:px-2.5 py-1 rounded-md bg-white border border-ink-border hover:border-forest-500 hover:bg-forest-50/50 text-ink-primary transition-colors text-xs font-medium"
            title="Inspect Dream11 T20 Fantasy Scoring Rules"
          >
            <Award className="w-3.5 h-3.5 text-forest-600 shrink-0" />
            <span className="hidden sm:inline text-ink-secondary">Rules:</span>
            <span className="font-semibold text-ink-primary hidden md:inline">Dream11 T20</span>
            <span className="text-[10px] font-mono text-forest-800 bg-forest-100 px-1.5 py-0.5 rounded font-semibold shrink-0">
              v{ruleset?.version || '2025.1.0'}
            </span>
          </button>

          {/* Engine Status Indicator */}
          <div
            className="flex items-center space-x-1.5 px-2 sm:px-2.5 py-1 rounded-md bg-white border border-ink-border text-xs text-ink-secondary font-medium shrink-0"
            title={
              geminiActive
                ? 'Gemini 3.8 Flash grounded explanation active'
                : 'Deterministic MCC Law rules engine active'
            }
          >
            {geminiActive ? (
              <>
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-forest-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-forest-600"></span>
                </span>
                <Sparkles className="w-3.5 h-3.5 text-forest-600 shrink-0 hidden sm:inline" />
                <span className="text-forest-700 font-medium hidden sm:inline">Gemini</span>
              </>
            ) : (
              <>
                <span className="h-2 w-2 rounded-full bg-forest-600 shrink-0"></span>
                <ShieldCheck className="w-3.5 h-3.5 text-forest-600 shrink-0 hidden sm:inline" />
                <span className="hidden sm:inline">Deterministic</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
