import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MatchMetadata,
  RulesetConfig,
  Delivery,
  SnapshotState,
  KeyMoment,
  PlayerInfo,
  FantasyTeamConfig,
  PlayerFantasyScore,
  BallFantasyImpact,
  EventExplanation,
} from './types';
import {
  fetchHealth,
  fetchMatches,
  fetchDeliveries,
  fetchSnapshot,
  fetchKeyMoments,
  fetchPlayers,
  fetchRuleset,
  computeCustomScores,
  explainDelivery,
} from './services/api';
import { Header } from './components/Header';
import { Scoreboard } from './components/Scoreboard';
import { KeyMomentsBar } from './components/KeyMomentsBar';
import { ReplayControls } from './components/ReplayControls';
import { FantasyTeamPanel } from './components/FantasyTeamPanel';
import { ExplainerPanel } from './components/ExplainerPanel';
import { TeamCustomizerModal } from './components/TeamCustomizerModal';
import { RulesModal } from './components/RulesModal';
import { PrivacyModal } from './components/PrivacyModal';
import { ContactModal } from './components/ContactModal';
import { AlertCircle, RefreshCw } from 'lucide-react';

const DEFAULT_TEAM: FantasyTeamConfig = {
  selected_players: [
    'V Kohli',
    'JJ Bumrah',
    'RG Sharma',
    'HH Pandya',
    'AR Patel',
    'Arshdeep Singh',
    'Q de Kock',
    'H Klaasen',
    'DA Miller',
    'K Rabada',
    'KA Maharaj',
  ],
  captain: 'V Kohli',
  vice_captain: 'JJ Bumrah',
};

export const App: React.FC = () => {
  // Core Match State
  const [matchId] = useState<string>('ind_sa_t20wc_2024_final');
  const [metadata, setMetadata] = useState<MatchMetadata | null>(null);
  const [ruleset, setRuleset] = useState<RulesetConfig | null>(null);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [roster, setRoster] = useState<PlayerInfo[]>([]);
  const [keyMoments, setKeyMoments] = useState<KeyMoment[]>([]);
  const [geminiActive, setGeminiActive] = useState<boolean>(false);

  // Replay State
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [snapshot, setSnapshot] = useState<SnapshotState | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Fantasy State
  const [teamConfig, setTeamConfig] = useState<FantasyTeamConfig>(DEFAULT_TEAM);
  const [playerScores, setPlayerScores] = useState<Record<string, PlayerFantasyScore>>({});
  const [teamTotal, setTeamTotal] = useState<number>(0);
  const [teamDelta, setTeamDelta] = useState<number>(0);
  const [currentDeltaImpact, setCurrentDeltaImpact] = useState<BallFantasyImpact | null>(null);

  // Explanation State
  const [explanation, setExplanation] = useState<EventExplanation | null>(null);
  const [isExplaining, setIsExplaining] = useState<boolean>(false);

  // Modals
  const [isCustomizerOpen, setIsCustomizerOpen] = useState<boolean>(false);
  const [isRulesOpen, setIsRulesOpen] = useState<boolean>(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState<boolean>(false);
  const [isContactOpen, setIsContactOpen] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Refs for timer & rate-limiting AI during fast playback
  const isPlayingRef = useRef(isPlaying);
  isPlayingRef.current = isPlaying;
  const currentIndexRef = useRef(currentIndex);
  currentIndexRef.current = currentIndex;

  // 1. Initial Data Loading
  useEffect(() => {
    async function initData() {
      try {
        const [health, matches, dlvList, pList, rSet, kmList] = await Promise.all([
          fetchHealth(),
          fetchMatches(),
          fetchDeliveries(matchId),
          fetchPlayers(matchId),
          fetchRuleset(matchId),
          fetchKeyMoments(matchId, 'all'),
        ]);

        setGeminiActive(health.gemini_ai_enabled);
        setMetadata(matches[0] || null);
        setDeliveries(dlvList);
        setRoster(pList);
        setRuleset(rSet);
        setKeyMoments(kmList);

        // Load initial ball (0)
        await loadBallState(0, DEFAULT_TEAM);
      } catch (err: any) {
        console.error('Initialization error:', err);
        setErrorMsg('Failed to initialize BoundaryIQ. Ensure backend is running at http://localhost:8000');
      }
    }
    initData();
  }, [matchId]);

  // 2. Load Delivery State in O(1)
  const loadBallState = useCallback(
    async (index: number, currentTeam: FantasyTeamConfig) => {
      try {
        const [snapData, scoresData] = await Promise.all([
          fetchSnapshot(matchId, index),
          computeCustomScores(index, currentTeam),
        ]);

        setSnapshot(snapData);
        setPlayerScores(scoresData.player_scores);
        setTeamTotal(scoresData.team_total);
        setTeamDelta(scoresData.team_delta);
        setCurrentDeltaImpact(scoresData.ball_delta);

        // If not playing at high speed, trigger explanation
        if (!isPlayingRef.current) {
          setIsExplaining(true);
          explainDelivery(matchId, index, currentTeam)
            .then((exp) => setExplanation(exp))
            .catch((e) => console.warn('Explanation error:', e))
            .finally(() => setIsExplaining(false));
        }
      } catch (e: any) {
        console.error(`Error loading ball ${index}:`, e);
      }
    },
    [matchId]
  );

  // When user stops or seeks, ensure explanation is fetched
  useEffect(() => {
    if (!isPlaying) {
      setIsExplaining(true);
      explainDelivery(matchId, currentIndex, teamConfig)
        .then((exp) => setExplanation(exp))
        .catch((e) => console.warn('Explanation error:', e))
        .finally(() => setIsExplaining(false));
    }
  }, [currentIndex, isPlaying, matchId, teamConfig]);

  // 3. Replay Autoplay Loop
  useEffect(() => {
    if (!isPlaying) return;

    const intervalTime = Math.max(250, 1500 / playbackSpeed);
    const interval = setInterval(() => {
      const nextIdx = currentIndexRef.current + 1;
      if (nextIdx >= deliveries.length) {
        setIsPlaying(false);
        return;
      }
      setCurrentIndex(nextIdx);
      loadBallState(nextIdx, teamConfig);
    }, intervalTime);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, deliveries.length, loadBallState, teamConfig]);

  // 4. Keyboard Shortcuts (Space, Left, Right)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying((prev) => !prev);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        if (currentIndexRef.current < deliveries.length - 1) {
          const next = currentIndexRef.current + 1;
          setCurrentIndex(next);
          loadBallState(next, teamConfig);
        }
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        if (currentIndexRef.current > 0) {
          const prev = currentIndexRef.current - 1;
          setCurrentIndex(prev);
          loadBallState(prev, teamConfig);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [deliveries.length, loadBallState, teamConfig]);

  // Replay Navigation Handlers
  const handleNext = () => {
    if (currentIndex < deliveries.length - 1) {
      const next = currentIndex + 1;
      setCurrentIndex(next);
      loadBallState(next, teamConfig);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      const prev = currentIndex - 1;
      setCurrentIndex(prev);
      loadBallState(prev, teamConfig);
    }
  };

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentIndex(0);
    loadBallState(0, teamConfig);
  };

  const handleSeek = (idx: number) => {
    setCurrentIndex(idx);
    loadBallState(idx, teamConfig);
  };

  const handleJumpToMoment = (idx: number) => {
    setIsPlaying(false);
    setCurrentIndex(idx);
    loadBallState(idx, teamConfig);
  };

  // Squad Presets
  const handleSelectPreset = (presetName: string) => {
    let newSquad: FantasyTeamConfig = DEFAULT_TEAM;
    if (presetName === 'india_heavy') {
      newSquad = {
        selected_players: [
          'RG Sharma', 'V Kohli', 'RR Pant', 'SA Yadav', 'AR Patel', 'HH Pandya', 'JJ Bumrah',
          'Q de Kock', 'H Klaasen', 'K Rabada', 'A Nortje'
        ],
        captain: 'V Kohli',
        vice_captain: 'HH Pandya'
      };
    } else if (presetName === 'sa_heavy') {
      newSquad = {
        selected_players: [
          'Q de Kock', 'H Klaasen', 'DA Miller', 'AK Markram', 'M Jansen', 'K Rabada', 'A Nortje',
          'V Kohli', 'JJ Bumrah', 'AR Patel', 'Arshdeep Singh'
        ],
        captain: 'H Klaasen',
        vice_captain: 'Q de Kock'
      };
    }
    setTeamConfig(newSquad);
    loadBallState(currentIndex, newSquad);
  };

  const handleSaveCustomTeam = (newTeam: FantasyTeamConfig) => {
    setTeamConfig(newTeam);
    loadBallState(currentIndex, newTeam);
  };

  return (
    <div className="min-h-screen bg-canvas text-ink-primary flex flex-col font-sans">
      {/* Header */}
      <Header
        metadata={metadata}
        ruleset={ruleset}
        geminiActive={geminiActive}
        onOpenRules={() => setIsRulesOpen(true)}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-3 py-4 sm:p-5 lg:p-6 space-y-4 min-w-0">
        {/* Error Alert */}
        {errorMsg && (
          <div className="p-3 rounded-md bg-sport-wicketBg border border-sport-wicketBorder text-sport-wicket text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-sport-wicket" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="px-2.5 py-1 rounded bg-sport-wicket text-white font-medium flex items-center space-x-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Top Cricket Scoreboard */}
        <Scoreboard
          scoreboard={snapshot}
          currentDelivery={deliveries[currentIndex] || null}
          onSelectBall={handleSeek}
        />

        {/* Key Moments Filter & Jump Bar */}
        <KeyMomentsBar
          keyMoments={keyMoments}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          currentIndex={currentIndex}
          onJumpToMoment={handleJumpToMoment}
        />

        {/* 3-Column Core Experience */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start min-w-0">
          {/* Left Column: Fantasy Team & Points (4 cols) */}
          <div className="lg:col-span-4 min-w-0 h-auto lg:h-[650px]">
            <FantasyTeamPanel
              playerScores={playerScores}
              teamTotal={teamTotal}
              teamDelta={teamDelta}
              currentDeltaImpact={currentDeltaImpact}
              teamConfig={teamConfig}
              onOpenCustomizer={() => setIsCustomizerOpen(true)}
              onSelectPreset={handleSelectPreset}
            />
          </div>

          {/* Center Column: Replay Controls & Match Event (4 cols) */}
          <div className="lg:col-span-4 min-w-0 flex flex-col space-y-3.5 h-auto lg:h-[650px]">
            <ReplayControls
              currentIndex={currentIndex}
              totalDeliveries={deliveries.length}
              currentDelivery={deliveries[currentIndex] || null}
              isPlaying={isPlaying}
              playbackSpeed={playbackSpeed}
              onTogglePlay={() => setIsPlaying((p) => !p)}
              onPrev={handlePrev}
              onNext={handleNext}
              onReset={handleReset}
              onSeek={handleSeek}
              onChangeSpeed={setPlaybackSpeed}
            />

            {/* Event Summary Card */}
            {snapshot && (
              <div className="p-3.5 rounded-lg bg-surface border border-ink-border shadow-sm space-y-2 min-w-0">
                <div className="flex items-center justify-between text-[10px] text-ink-secondary font-semibold uppercase tracking-wider">
                  <span>Match Action Live Feed</span>
                  <span className="text-forest-700 font-mono font-semibold">Over {snapshot.overs_display}</span>
                </div>
                <p className="text-xs font-semibold text-ink-primary leading-relaxed break-words">
                  {snapshot.delivery_event.summary}
                </p>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] text-ink-secondary pt-2 border-t border-ink-border min-w-0">
                  <span className="truncate">
                    Striker: <strong className="text-ink-primary font-semibold">{snapshot.striker.name}</strong> ({snapshot.striker.runs}r, {snapshot.striker.balls}b)
                  </span>
                  <span className="truncate">
                    Bowler: <strong className="text-ink-primary font-semibold">{snapshot.bowler.name}</strong> ({snapshot.bowler.wickets}/{snapshot.bowler.runs_conceded})
                  </span>
                </div>
              </div>
            )}

            {/* Interactive Delivery Log / Over Feed */}
            {snapshot && (
              <div className="h-64 lg:flex-1 bg-surface border border-ink-border rounded-lg p-3 shadow-sm flex flex-col min-h-0 overflow-hidden">
                <div className="flex items-center justify-between pb-2 border-b border-ink-border text-xs mb-2">
                  <span className="text-[10px] font-semibold text-ink-secondary uppercase tracking-wider">
                    Recent Delivery Feed
                  </span>
                  <span className="font-mono text-[10px] text-ink-muted">
                    Click any ball to replay
                  </span>
                </div>
                <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5">
                  {snapshot.recent_balls.slice().reverse().map((b) => {
                    const isSelected = b.index === currentIndex;
                    const dObj = deliveries[b.index];
                    let badgeClass = 'bg-canvas text-ink-primary border-ink-border';
                    let label = b.total_runs.toString();

                    if (b.is_wicket) {
                      badgeClass = 'bg-sport-wicketBg text-sport-wicket border-sport-wicketBorder font-bold';
                      label = 'W';
                    } else if (b.is_six) {
                      badgeClass = 'bg-forest-100 text-forest-800 border-forest-300 font-bold';
                      label = '6';
                    } else if (b.is_four) {
                      badgeClass = 'bg-forest-50 text-forest-700 border-forest-200 font-bold';
                      label = '4';
                    } else if (b.extra_type) {
                      badgeClass = 'bg-amber-50 text-amber-800 border-amber-200 font-mono text-[10px]';
                      label = b.extra_type === 'wides' ? `${b.total_runs}wd` : `${b.total_runs}nb`;
                    } else if (b.total_runs === 0) {
                      label = '•';
                    }

                    return (
                      <div
                        key={b.index}
                        onClick={() => handleSeek(b.index)}
                        className={`p-2 rounded-md border text-xs cursor-pointer flex items-center justify-between transition-colors ${
                          isSelected
                            ? 'bg-forest-50/60 border-forest-500 font-medium'
                            : 'bg-white border-ink-border hover:bg-canvas'
                        }`}
                      >
                        <div className="flex items-center space-x-2 truncate min-w-0">
                          <span className={`w-5 h-5 rounded text-[10px] font-mono flex items-center justify-center border flex-shrink-0 ${badgeClass}`}>
                            {label}
                          </span>
                          <span className="font-mono text-[11px] text-ink-muted font-medium flex-shrink-0">
                            {b.over_display}
                          </span>
                          <span className="text-[11px] text-ink-primary truncate min-w-0">
                            {dObj ? `${dObj.bowler} to ${dObj.batter}` : 'Delivery'}
                          </span>
                        </div>
                        <span className="font-mono text-[10px] text-ink-secondary ml-2 flex-shrink-0">
                          {b.total_runs} run{b.total_runs !== 1 ? 's' : ''}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Grounded AI Match & Fantasy Explainer (4 cols) */}
          <div className="lg:col-span-4 min-w-0 h-auto lg:h-[650px]">
            <ExplainerPanel
              explanation={explanation}
              ballDelta={currentDeltaImpact}
              currentDelivery={deliveries[currentIndex] || null}
              isLoading={isExplaining}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-ink-border bg-surface py-4 text-center text-xs text-ink-secondary">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex flex-wrap items-center justify-center sm:justify-start gap-x-3 gap-y-1">
            <p>
              <strong>BoundaryIQ</strong> — Sports Analytics &amp; Fantasy Cricket Explainer.
            </p>
            <span className="hidden sm:inline text-ink-muted">•</span>
            <button
              onClick={() => setIsRulesOpen(true)}
              className="text-ink-secondary hover:text-forest-700 underline font-medium transition-colors"
            >
              Scoring Rules (v{ruleset?.version || '2025.1.0'})
            </button>
            <span className="text-ink-muted">•</span>
            <button
              onClick={() => setIsPrivacyOpen(true)}
              className="text-ink-secondary hover:text-forest-700 underline font-medium transition-colors"
            >
              Privacy &amp; Legal
            </button>
            <span className="text-ink-muted">•</span>
            <button
              onClick={() => setIsContactOpen(true)}
              className="text-ink-secondary hover:text-forest-700 underline font-medium transition-colors"
            >
              Feedback &amp; Contact
            </button>
          </div>
          <p className="text-[11px] text-ink-muted">
            Match data courtesy of{' '}
            <a
              href="https://cricsheet.org"
              target="_blank"
              rel="noreferrer"
              className="text-forest-700 font-medium hover:underline"
            >
              Cricsheet
            </a>{' '}
            (ODC-BY 1.0 License).
          </p>
        </div>
      </footer>

      {/* Modals */}
      <TeamCustomizerModal
        isOpen={isCustomizerOpen}
        onClose={() => setIsCustomizerOpen(false)}
        roster={roster}
        currentTeam={teamConfig}
        onSave={handleSaveCustomTeam}
      />

      <RulesModal
        isOpen={isRulesOpen}
        onClose={() => setIsRulesOpen(false)}
        ruleset={ruleset}
      />

      <PrivacyModal
        isOpen={isPrivacyOpen}
        onClose={() => setIsPrivacyOpen(false)}
      />

      <ContactModal
        isOpen={isContactOpen}
        onClose={() => setIsContactOpen(false)}
      />
    </div>
  );
};

export default App;
