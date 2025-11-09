import { useMemo, useState } from "react";
import {
  internalNamesToDisplayNames,
  internalDisplayMapToDisplayNamesList,
} from "../../utils/gameModes";
import { ChevronUp } from "lucide-react";
import "./gameModeFilter.css";

export function GameModeFilter({
  gameModes,
  selected,
  onChange,
}: Readonly<{
  gameModes: Record<string, string>;
  selected: string[]; // internal keys currently selected
  onChange: (next: string[]) => void; // emit internal keys
}>) {
  const [isExpanded, setIsExpanded] = useState(false); // init with hidden option

  // Build map: internal -> display
  const gameModesMap = useMemo(
    () => internalNamesToDisplayNames(gameModes),
    [gameModes]
  );

  // Get unique display names
  const uniqueDisplayNames = useMemo(
    () => internalDisplayMapToDisplayNamesList(gameModesMap),
    [gameModesMap]
  );

  // TODO upon all selected game modes, emit empty game modes array --> same result for the backend
  // Create options with display names and their corresponding internal names
  const options = useMemo(() => {
    return uniqueDisplayNames.map((display) => {
      // Find all internal names that map to this display name
      const internals: string[] = [];
      for (const [internal, displayName] of gameModesMap.entries()) {
        if (displayName === display) {
          internals.push(internal);
        }
      }
      return { display, internals };
    });
  }, [uniqueDisplayNames, gameModesMap]);

  const isSelected = (internals: string[]) =>
    internals.some((internal) => selected.includes(internal));

  const toggle = (internals: string[]) => {
    const isCurrentlySelected = isSelected(internals);
    if (isCurrentlySelected) {
      // Remove all internals for this display name
      onChange(selected.filter((s) => !internals.includes(s)));
    } else {
      // Add all internals for this display name
      onChange([...selected, ...internals]);
    }
  };

  const selectAll = () => {
    // Get all internal names from all options
    const allInternals = options.flatMap((option) => option.internals);
    onChange(allInternals);
  };

  const clearAll = () => {
    onChange([]);
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
        {options.map(({ internals, display }) => (
          <button
            key={display}
            type="button"
            className={`game-mode-filter-component-tag ${
              isSelected(internals) ? "is-selected" : ""
            }`}
            onClick={() => toggle(internals)}
            aria-pressed={isSelected(internals)}
          >
            <span className="game-mode-filter-component-tag-text">
              {display}
            </span>
          </button>
        ))}
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
