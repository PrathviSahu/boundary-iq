import React from 'react';
import { KeyMoment } from '../types';
import { Zap, ShieldAlert, Award, Layers } from 'lucide-react';

interface KeyMomentsBarProps {
  keyMoments: KeyMoment[];
  selectedCategory: string;
  onSelectCategory: (category: string) => void;
  currentIndex: number;
  onJumpToMoment: (index: number) => void;
}

export const KeyMomentsBar: React.FC<KeyMomentsBarProps> = ({
  keyMoments,
  selectedCategory,
  onSelectCategory,
  currentIndex,
  onJumpToMoment,
}) => {
  const categories = [
    { id: 'all', label: 'All Key Moments', icon: Layers },
    { id: 'wickets', label: 'Wickets', icon: ShieldAlert },
    { id: 'boundaries', label: 'Boundaries (4s & 6s)', icon: Zap },
    { id: 'milestones', label: 'Fantasy Milestones', icon: Award },
  ];

  const filteredMoments = keyMoments.filter((m) => {
    if (selectedCategory === 'all') return true;
    if (selectedCategory === 'wickets') return m.category === 'wicket';
    if (selectedCategory === 'boundaries') return m.category === 'boundary';
    if (selectedCategory === 'milestones') return m.category === 'milestone' || m.category === 'climax';
    return true;
  });

  return (
    <div className="bg-surface border border-ink-border rounded-lg p-3.5 sm:p-4 shadow-sm space-y-3">
      {/* Category Filter Row */}
      <div className="flex items-center justify-between flex-wrap gap-2.5 pb-2.5 border-b border-ink-border">
        <div className="flex items-center space-x-1.5 text-xs text-ink-secondary font-semibold uppercase tracking-wider">
          <span>Key Match Moments</span>
          <span className="text-ink-muted">({filteredMoments.length})</span>
        </div>

        <div className="flex items-center space-x-1.5 overflow-x-auto max-w-full pb-0.5">
          {categories.map((c) => {
            const Icon = c.icon;
            const isActive = selectedCategory === c.id;
            return (
              <button
                key={c.id}
                onClick={() => onSelectCategory(c.id)}
                className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-forest-600 text-white font-semibold'
                    : 'bg-canvas text-ink-secondary hover:text-ink-primary hover:bg-forest-50/70 border border-ink-border'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{c.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Horizontal List of Key Moments */}
      <div className="flex items-stretch space-x-3 overflow-x-auto pb-1.5 pt-0.5">
        {filteredMoments.map((m) => {
          const isCurrent = m.delivery_index === currentIndex;

          let badgeColor = 'bg-canvas text-ink-secondary border-ink-border';
          let borderHighlight = isCurrent
            ? 'border-forest-600 bg-forest-50/40 ring-1 ring-forest-600 shadow-xs'
            : 'border-ink-border bg-white hover:border-forest-300 hover:bg-forest-50/20';

          if (m.category === 'wicket') {
            badgeColor = 'bg-sport-wicketBg text-sport-wicket border-sport-wicketBorder font-semibold';
          } else if (m.category === 'boundary') {
            badgeColor = 'bg-forest-50 text-forest-700 border-forest-200 font-semibold';
          } else if (m.category === 'milestone') {
            badgeColor = 'bg-sport-milestoneBg text-sport-milestone border-sport-milestoneBorder font-semibold';
          } else if (m.category === 'climax') {
            badgeColor = 'bg-forest-100 text-forest-800 border-forest-300 font-semibold';
          }

          return (
            <button
              key={`${m.delivery_index}-${m.over_display}`}
              onClick={() => onJumpToMoment(m.delivery_index)}
              className={`flex-shrink-0 w-72 sm:w-80 p-3 rounded-lg border text-left transition-all flex flex-col justify-between ${borderHighlight}`}
            >
              <div className="space-y-1 mb-2">
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${badgeColor}`}>
                    Over {m.over_display}
                  </span>
                  <span className="text-[10px] font-semibold uppercase text-ink-secondary tracking-wider">
                    {m.category}
                  </span>
                </div>

                <h4 className="text-xs font-bold text-ink-primary leading-snug">
                  {m.title}
                </h4>

                <p className="text-[11px] text-ink-secondary leading-relaxed line-clamp-2">
                  {m.subtitle}
                </p>
              </div>

              {m.points_headline && (
                <div className="text-[11px] font-mono font-medium text-forest-800 bg-forest-50 px-2 py-1 rounded border border-forest-200/70 leading-snug break-words">
                  {m.points_headline}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
