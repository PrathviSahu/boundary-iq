import React from 'react';
import { Play, Pause, SkipBack, SkipForward, RotateCcw } from 'lucide-react';
import { Delivery } from '../types';

interface ReplayControlsProps {
  currentIndex: number;
  totalDeliveries: number;
  currentDelivery: Delivery | null;
  isPlaying: boolean;
  playbackSpeed: number;
  onTogglePlay: () => void;
  onPrev: () => void;
  onNext: () => void;
  onReset: () => void;
  onSeek: (index: number) => void;
  onChangeSpeed: (speed: number) => void;
}

export const ReplayControls: React.FC<ReplayControlsProps> = ({
  currentIndex,
  totalDeliveries,
  currentDelivery,
  isPlaying,
  playbackSpeed,
  onTogglePlay,
  onPrev,
  onNext,
  onReset,
  onSeek,
  onChangeSpeed,
}) => {
  const speeds = [0.5, 1, 2, 5];

  return (
    <div className="bg-surface border border-ink-border rounded-lg p-3 sm:p-3.5 shadow-sm space-y-3 min-w-0">
      {/* Current Delivery Header */}
      {currentDelivery && (
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2.5 border-b border-ink-border min-w-0">
          <div className="flex items-center space-x-2 min-w-0">
            <span className="px-2 py-0.5 rounded bg-forest-100 border border-forest-200 text-forest-800 font-mono font-bold text-xs shrink-0">
              Over {currentDelivery.over_display}
            </span>
            <div className="text-xs truncate">
              <span className="font-semibold text-ink-primary">{currentDelivery.bowler}</span>
              <span className="text-ink-muted"> to </span>
              <span className="font-semibold text-ink-primary">{currentDelivery.batter}</span>
            </div>
          </div>

          <div className="flex items-center space-x-1.5 flex-wrap shrink-0">
            {currentDelivery.is_wicket && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sport-wicketBg text-sport-wicket border border-sport-wicketBorder">
                WICKET
              </span>
            )}
            {currentDelivery.is_six && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-forest-100 text-forest-800 border border-forest-300">
                MAXIMUM 6
              </span>
            )}
            {currentDelivery.is_four && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-forest-50 text-forest-700 border border-forest-200">
                FOUR
              </span>
            )}
            {currentDelivery.extra_type && (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-50 text-amber-800 border border-amber-200">
                {currentDelivery.extra_type.toUpperCase()} ({currentDelivery.extra_runs})
              </span>
            )}
          </div>
        </div>
      )}

      {/* Control Buttons & Playback Speed - Two Rows on Mobile, One Row on Desktop */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 min-w-0">
        {/* Navigation Buttons Row */}
        <div className="flex items-center justify-between sm:justify-start space-x-1.5 w-full sm:w-auto">
          {/* Reset */}
          <button
            onClick={onReset}
            className="p-1.5 rounded-md border border-ink-border bg-white hover:bg-forest-50 text-ink-secondary hover:text-ink-primary transition-colors shrink-0"
            title="Reset to Ball 1 (Over 0.1)"
            aria-label="Reset replay"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Previous Delivery */}
          <button
            onClick={onPrev}
            disabled={currentIndex <= 0}
            className="p-1.5 rounded-md border border-ink-border bg-white hover:bg-forest-50 disabled:opacity-40 disabled:hover:bg-white text-ink-secondary hover:text-ink-primary transition-colors shrink-0"
            title="Previous Delivery (Left Arrow)"
            aria-label="Previous delivery"
          >
            <SkipBack className="w-4 h-4" />
          </button>

          {/* Play / Pause Primary */}
          <button
            onClick={onTogglePlay}
            className={`flex-1 sm:flex-initial px-4 py-1.5 rounded-md font-semibold text-xs flex items-center justify-center space-x-1.5 transition-colors shadow-xs ${
              isPlaying
                ? 'bg-amber-600 hover:bg-amber-500 text-white'
                : 'bg-forest-600 hover:bg-forest-700 text-white'
            }`}
            title="Play / Pause Replay (Spacebar)"
            aria-label={isPlaying ? 'Pause replay' : 'Play replay'}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5 fill-current" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Play Replay</span>
              </>
            )}
          </button>

          {/* Next Delivery */}
          <button
            onClick={onNext}
            disabled={currentIndex >= totalDeliveries - 1}
            className="p-1.5 rounded-md border border-ink-border bg-white hover:bg-forest-50 disabled:opacity-40 disabled:hover:bg-white text-ink-secondary hover:text-ink-primary transition-colors shrink-0"
            title="Next Delivery (Right Arrow)"
            aria-label="Next delivery"
          >
            <SkipForward className="w-4 h-4" />
          </button>
        </div>

        {/* Speed Controls Row */}
        <div className="flex items-center justify-center space-x-1 bg-canvas p-1 sm:p-0.5 rounded-md border border-ink-border text-xs w-full sm:w-auto shrink-0">
          <span className="text-[10px] text-ink-muted px-1.5 font-medium">Speed:</span>
          {speeds.map((s) => (
            <button
              key={s}
              onClick={() => onChangeSpeed(s)}
              className={`flex-1 sm:flex-initial px-2.5 sm:px-2 py-1 sm:py-0.5 rounded text-[11px] font-mono transition-colors text-center ${
                playbackSpeed === s
                  ? 'bg-surface text-forest-700 font-bold shadow-xs border border-ink-border'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Scrubber Timeline Bar */}
      <div className="pt-1 space-y-1">
        <input
          type="range"
          min={0}
          max={Math.max(0, totalDeliveries - 1)}
          value={currentIndex}
          onChange={(e) => onSeek(parseInt(e.target.value, 10))}
          className="w-full h-1.5 bg-forest-100 rounded-lg appearance-none cursor-pointer accent-forest-600 focus:outline-none"
          aria-label="Replay scrubber"
        />
        <div className="flex justify-between text-[10px] font-mono text-ink-muted">
          <span>0.1 (Inn 1)</span>
          <span className="hidden xs:inline">20.0 (Mid-Inn)</span>
          <span className="hidden sm:inline">Chase</span>
          <span>Final Over</span>
        </div>
      </div>
    </div>
  );
};
