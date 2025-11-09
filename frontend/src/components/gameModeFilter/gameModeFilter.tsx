import { useMemo, useState, useEffect } from "react";
import {
  internalNamesToDisplayNames,
  internalDisplayMapToDisplayNamesList,
} from "../../utils/gameModes";
import { ChevronUp } from "lucide-react";
import "./gameModeFilter.css";

/**
 * GameModeFilter component with backend optimization while preserving visual behavior.
 *
 * OPTIMIZATION STRATEGY:
 * - "Select All" button → Emits empty array [] (optimization) but shows all options selected visually
 * - Manual selection → Uses explicit arrays, shows exactly what's selected visually
 * - "Clear" button → Emits empty array [] but shows no options selected visually
 *
 * The visual representation is decoupled from the emitted value to allow backend optimization
 * while maintaining intuitive user experience.
 */
export function GameModeFilter({
  gameModes,
  selected,
  onChange,
}: Readonly<{
  gameModes: Record<string, string>;
  selected: string[]; // internal keys currently selected
  onChange: (next: string[]) => void; // emit internal keys
}>) {
  const [isExpanded, setIsExpanded] = useState(false);
  // Local flag to interpret [] as "all selected" (true) or "cleared/default" (false)
  const [isAllSelectedMode, setIsAllSelectedMode] = useState(false);

  // Build map: internal -> display (assumed Map or compatible entry iterator)
  const gameModesMap = useMemo(
    () => internalNamesToDisplayNames(gameModes),
    [gameModes]
  );

  // Unique display names
  const uniqueDisplayNames = useMemo(
    () => internalDisplayMapToDisplayNamesList(gameModesMap),
    [gameModesMap]
  );

  // Options: group internals by display name
  const options = useMemo(() => {
    return uniqueDisplayNames.map((display) => {
      const internals: string[] = [];
      for (const [internal, displayName] of gameModesMap.entries()) {
        if (displayName === display) internals.push(internal);
      }
      return { display, internals };
    });
  }, [uniqueDisplayNames, gameModesMap]);

  // All internals (deduped to ensure unique game modes) and set for fast operations
  const allInternals = useMemo(() => {
    const s = new Set<string>();
    for (const opt of options) for (const i of opt.internals) s.add(i);
    return Array.from(s);
  }, [options]);

  const allInternalsSet = useMemo(() => new Set(allInternals), [allInternals]);

  // Keep local mode consistent when parent sends explicit non-empty selections
  useEffect(() => {
    if (selected.length > 0) setIsAllSelectedMode(false);
  }, [selected]);

  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const isSelected = (internals: string[]) => {
    // In "select all" mode with empty emitted array, everything is visually selected
    if (selected.length === 0 && isAllSelectedMode) return true;
    // Otherwise selected if any internal is present
    return internals.some((i) => selectedSet.has(i));
  };

  const setsAreEqual = (a: Set<string>, b: Set<string>) =>
    a.size === b.size && Array.from(a).every((x) => b.has(x));

  const toggle = (internals: string[]) => {
    const currentlySelected = isSelected(internals);

    // If currently selected
    if (currentlySelected) {
      if (selected.length === 0 && isAllSelectedMode) {
        // We were in "select all" ([]) → switch to explicit minus this group
        const next = new Set(allInternals);
        for (const i of internals) next.delete(i);
        setIsAllSelectedMode(false);
        onChange(Array.from(next));
        return;
      }
      // Remove this group's internals
      const next = new Set(selectedSet);
      for (const i of internals) next.delete(i);
      // If removal results in empty explicit set, it's a true "none selected" state
      setIsAllSelectedMode(false);
      onChange(Array.from(next));
      return;
    }

    // If currently NOT selected → add this group's internals (union)
    const next = new Set(selectedSet);
    for (const i of internals) next.add(i);

    // If union equals "all internals", optimize to [] and flip visual to "all selected"
    if (setsAreEqual(next, allInternalsSet)) {
      setIsAllSelectedMode(true);
      onChange([]);
    } else {
      setIsAllSelectedMode(false);
      onChange(Array.from(next));
    }
  };

  const selectAll = () => {
    setIsAllSelectedMode(true);
    onChange([]); // optimization: [] means "all selected" (no filtering) for backend
  };

  const clearAll = () => {
    setIsAllSelectedMode(false);
    onChange([]); // same payload (game modes), but local flag makes it visually "none"
  };

  return (
    <div className="game-mode-filter-container">
      <button
        type="button"
        className="game-mode-filter-component-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="game-mode-filter-component-title">Game Modes</span>
        <ChevronUp
          className={`game-mode-filter-component-toggle ${
            isExpanded ? "" : "collapsed"
          }`}
        />
      </button>

      <div
        id="game-mode-filter-grid"
        className={`game-mode-filter-component-grid ${
          isExpanded ? "" : "hidden"
        }`}
      >
        {options.map(({ internals, display }) => {
          const selectedVisual = isSelected(internals);
          return (
            <button
              key={display}
              type="button"
              className={`game-mode-filter-component-tag ${
                selectedVisual ? "is-selected" : ""
              }`}
              onClick={() => toggle(internals)}
              aria-pressed={selectedVisual}
            >
              <span className="game-mode-filter-component-tag-text">
                {display}
              </span>
            </button>
          );
        })}

        <div className="game-mode-filter-component-actions">
          <button
            type="button"
            className="game-mode-filter-component-action-button game-mode-filter-component-select-all"
            onClick={selectAll}
          >
            Select All
          </button>
          <button
            type="button"
            className="game-mode-filter-component-action-button game-mode-filter-component-clear"
            onClick={clearAll}
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}
