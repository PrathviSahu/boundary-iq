import React, { useState } from 'react';
import { X, Check, Users, AlertTriangle } from 'lucide-react';
import { PlayerInfo, FantasyTeamConfig } from '../types';

interface TeamCustomizerModalProps {
  isOpen: boolean;
  onClose: () => void;
  roster: PlayerInfo[];
  currentTeam: FantasyTeamConfig;
  onSave: (newTeam: FantasyTeamConfig) => void;
}

export const TeamCustomizerModal: React.FC<TeamCustomizerModalProps> = ({
  isOpen,
  onClose,
  roster,
  currentTeam,
  onSave,
}) => {
  const [selected, setSelected] = useState<string[]>(currentTeam.selected_players);
  const [captain, setCaptain] = useState<string>(currentTeam.captain);
  const [viceCaptain, setViceCaptain] = useState<string>(currentTeam.vice_captain);
  const [filterRole, setFilterRole] = useState<string>('ALL');
  const [filterTeam, setFilterTeam] = useState<string>('ALL');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const togglePlayer = (name: string) => {
    setErrorMsg(null);
    if (selected.includes(name)) {
      if (selected.length <= 1) {
        setErrorMsg('Team cannot be empty');
        return;
      }
      const updated = selected.filter((p) => p !== name);
      setSelected(updated);
      if (captain === name) setCaptain(updated[0] || '');
      if (viceCaptain === name) setViceCaptain(updated[1] || updated[0] || '');
    } else {
      if (selected.length >= 11) {
        setErrorMsg('Squad limit reached (Maximum 11 players)');
        return;
      }
      setSelected([...selected, name]);
    }
  };

  const handleSave = () => {
    if (selected.length !== 11) {
      setErrorMsg(`Please select exactly 11 players (currently ${selected.length})`);
      return;
    }
    if (!captain || !selected.includes(captain)) {
      setErrorMsg('Please select a valid Captain from your chosen 11');
      return;
    }
    if (!viceCaptain || !selected.includes(viceCaptain)) {
      setErrorMsg('Please select a valid Vice-Captain from your chosen 11');
      return;
    }
    if (captain === viceCaptain) {
      setErrorMsg('Captain and Vice-Captain must be two different players');
      return;
    }

    onSave({
      selected_players: selected,
      captain,
      vice_captain: viceCaptain,
    });
    onClose();
  };

  const teams = Array.from(new Set(roster.map((p) => p.team))).filter(Boolean);

  const filteredRoster = roster.filter((p) => {
    const roleMatch = filterRole === 'ALL' || p.role === filterRole;
    const teamMatch = filterTeam === 'ALL' || p.team === filterTeam;
    return roleMatch && teamMatch;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-white border border-ink-border rounded-lg shadow-xl overflow-hidden my-6 max-h-[92vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ink-border bg-white">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-md bg-forest-50 border border-forest-200 text-forest-700">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-ink-primary">Customise Fantasy XI</h2>
              <p className="text-xs text-ink-secondary">
                Select 11 players and designate Captain (2.0x) and Vice-Captain (1.5x)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-ink-secondary hover:text-ink-primary hover:bg-canvas transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Squad Status Bar */}
        <div className="px-6 py-2.5 bg-canvas border-b border-ink-border flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1.5">
              <span className="text-ink-secondary">Selected:</span>
              <span
                className={`font-mono font-bold px-2 py-0.5 rounded text-xs ${
                  selected.length === 11
                    ? 'bg-forest-100 text-forest-800 border border-forest-300'
                    : 'bg-amber-50 text-amber-800 border border-amber-200'
                }`}
              >
                {selected.length} / 11
              </span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="text-ink-secondary">Captain (2x):</span>
              <span className="font-semibold text-forest-700">{captain || 'None'}</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="text-ink-secondary">Vice-Captain (1.5x):</span>
              <span className="font-semibold text-ink-primary">{viceCaptain || 'None'}</span>
            </div>
          </div>

          {errorMsg && (
            <div className="flex items-center space-x-1.5 text-sport-wicket bg-sport-wicketBg px-2.5 py-0.5 rounded border border-sport-wicketBorder text-xs">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Role & Team Filters */}
        <div className="px-6 py-2.5 bg-white border-b border-ink-border flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="text-ink-secondary mr-1">Role:</span>
            {['ALL', 'WK', 'BAT', 'AR', 'BOWL'].map((r) => (
              <button
                key={r}
                onClick={() => setFilterRole(r)}
                className={`px-2 py-0.5 rounded text-xs transition-colors ${
                  filterRole === r
                    ? 'bg-forest-600 text-white font-medium'
                    : 'bg-canvas text-ink-secondary hover:text-ink-primary border border-ink-border'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-1.5">
            <span className="text-ink-secondary mr-1">Team:</span>
            {['ALL', ...teams].map((t) => (
              <button
                key={t}
                onClick={() => setFilterTeam(t)}
                className={`px-2 py-0.5 rounded text-xs transition-colors ${
                  filterTeam === t
                    ? 'bg-forest-600 text-white font-medium'
                    : 'bg-canvas text-ink-secondary hover:text-ink-primary border border-ink-border'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Player Roster Grid */}
        <div className="p-6 overflow-y-auto space-y-2 flex-1 bg-canvas">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {filteredRoster.map((player) => {
              const isSelected = selected.includes(player.name);
              const isC = captain === player.name;
              const isVC = viceCaptain === player.name;

              return (
                <div
                  key={player.name}
                  onClick={() => togglePlayer(player.name)}
                  className={`flex items-center justify-between p-2.5 rounded-md border transition-all cursor-pointer select-none ${
                    isSelected
                      ? 'bg-forest-50/40 border-forest-500 shadow-xs'
                      : 'bg-white border-ink-border hover:border-forest-300'
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center transition-colors ${
                        isSelected
                          ? 'bg-forest-600 text-white'
                          : 'border border-ink-border bg-canvas text-transparent'
                      }`}
                    >
                      <Check className="w-3 h-3 stroke-[3]" />
                    </div>

                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="font-semibold text-ink-primary text-xs">{player.name}</span>
                        <span
                          className={`text-[9px] px-1 py-0.2 rounded font-mono font-medium ${
                            player.team === 'India'
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : 'bg-forest-50 text-forest-700 border border-forest-200'
                          }`}
                        >
                          {player.team === 'India' ? 'IND' : 'SA'}
                        </span>
                        <span className="text-[9px] px-1 py-0.2 rounded bg-canvas text-ink-secondary font-mono border border-ink-border">
                          {player.role}
                        </span>
                      </div>
                      <span className="text-[10px] text-ink-secondary font-mono">Credits: {player.credits}</span>
                    </div>
                  </div>

                  {isSelected && (
                    <div
                      className="flex items-center space-x-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {/* Captain Button */}
                      <button
                        onClick={() => {
                          if (isVC) setViceCaptain(captain);
                          setCaptain(player.name);
                        }}
                        className={`w-6 h-6 rounded text-[11px] font-bold font-mono transition-colors flex items-center justify-center ${
                          isC
                            ? 'bg-forest-600 text-white shadow-xs'
                            : 'bg-canvas text-ink-secondary hover:text-ink-primary border border-ink-border'
                        }`}
                        title="Set as Captain (2.0x)"
                      >
                        C
                      </button>

                      {/* Vice Captain Button */}
                      <button
                        onClick={() => {
                          if (isC) setCaptain(viceCaptain);
                          setViceCaptain(player.name);
                        }}
                        className={`w-6 h-6 rounded text-[11px] font-bold font-mono transition-colors flex items-center justify-center ${
                          isVC
                            ? 'bg-ink-primary text-white shadow-xs'
                            : 'bg-canvas text-ink-secondary hover:text-ink-primary border border-ink-border'
                        }`}
                        title="Set as Vice-Captain (1.5x)"
                      >
                        VC
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-ink-border bg-white flex items-center justify-between text-xs">
          <span className="text-ink-secondary">
            Points recalculate deterministically on every match ball
          </span>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-md text-ink-secondary hover:text-ink-primary hover:bg-canvas transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 rounded-md bg-forest-600 hover:bg-forest-700 text-white font-semibold transition-colors flex items-center space-x-1.5 shadow-xs"
            >
              <Check className="w-3.5 h-3.5 stroke-[2.5]" />
              <span>Apply XI ({selected.length}/11)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
