import { useMemo, useEffect } from "react";
import {
  internalNamesToDisplayNames,
  internalDisplayMapToDisplayNamesList,
} from "../../utils/gameModes";
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

  // Initialize with ALL options selected if no selection exists
  // That takes effect upon initialization but also when the user toggles off all
  // game modes, that is the same as toggling them all on
  useEffect(() => {
    if (selected.length === 0 && options.length > 0) {
      onChange(options.flatMap((o) => o.internals));
    }
  }, [options, selected.length, onChange]);

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

  return (
    <div className="game-mode-filter-component-grid">
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
          <span className="game-mode-filter-component-tag-text">{display}</span>
        </button>
      ))}
    </div>
  );
}
