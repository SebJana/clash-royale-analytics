import { useMemo, useState, useEffect, useRef } from "react";
import {
  internalNamesToDisplayNames,
  internalDisplayMapToDisplayNamesList,
} from "../../utils/gameModes";
import { ChevronUp } from "lucide-react";
import "./gameModeFilter.css";

/**
 * Utility function to get unique items from an array
 * @param arr - Array of strings
 * @returns Array with duplicate strings removed
 */
const uniq = (arr: string[]) => Array.from(new Set(arr));

/**
 * GameModeFilter Component
 *
 * A collapsible filter component for selecting game modes. Handles the complexity of
 * mapping internal API keys to user-friendly display names, allowing multiple internal
 * modes to share the same display name.
 *
 * Key behaviors:
 * - Empty selection array means "all modes selected" (no filtering)
 * - Visual state may differ from API state for better UX
 * - Supports "Select All" and "Clear" actions
 */

// TODO upon any of the other filters changing, the full game mode selection to empty array doesn't work anymore
export function GameModeFilter({
  gameModes,
  selected,
  onChange,
}: Readonly<{
  gameModes: Record<string, string>; // Map of internal keys to raw names from API
  selected: string[]; // Internal keys currently selected/used by API
  onChange: (next: string[]) => void; // Callback to emit internal keys for API (empty array when all selected or none)
}>) {
  // Controls whether the filter options are expanded or collapsed
  const [isExpanded, setIsExpanded] = useState(false);

  // Local visual state for selected modes (internal keys)
  // This can differ from the parent's `selected` prop for better UX
  const [displaySelectedModes, setDisplaySelectedModes] = useState<string[]>(
    []
  );

  // Convert raw game mode names from API to user-friendly display names
  // Creates a Map: internal key -> display name
  const gameModesMap = useMemo(
    () => internalNamesToDisplayNames(gameModes),
    [gameModes]
  );

  // Extract unique display names from the map
  // Multiple internal keys may map to the same display name
  const uniqueDisplayNames = useMemo(
    () => internalDisplayMapToDisplayNamesList(gameModesMap),
    [gameModesMap]
  );

  // Group internal keys by their display names
  // Each option represents one filter button with its associated internal keys
  const options = useMemo(() => {
    return uniqueDisplayNames.map((display) => {
      const internals: string[] = [];
      // Find all internal keys that map to this display name
      for (const [internal, displayName] of gameModesMap.entries()) {
        if (displayName === display) internals.push(internal);
      }
      return { display, internals };
    });
  }, [uniqueDisplayNames, gameModesMap]);

  // Complete list of all internal keys (deduplicated)
  // Used for "Select All" functionality and comparison logic
  const allInternals = useMemo(
    () => uniq(options.flatMap((o) => o.internals)),
    [options]
  );

  // Track whether we've initialized the component from props
  // This prevents the UI from resetting when parent sends empty array after user actions
  const didInit = useRef(false);

  /**
   * Initialize and sync local state with parent props
   *
   * Complex logic to handle the fact that an empty `selected` array can mean:
   * 1. "All modes selected" (initial state)
   * 2. "No filtering applied" (after user clicks Clear)
   *
   * We only auto-sync on the first render, then only when parent provides
   * a concrete subset of modes.
   */
  useEffect(() => {
    if (!didInit.current) {
      // Initial setup: empty selection means "all selected" visually
      setDisplaySelectedModes(
        selected.length === 0 ? allInternals : uniq(selected)
      );
      didInit.current = true;
      return;
    }

    // On subsequent updates, only sync when parent provides concrete selection
    // This preserves local visual state when parent sends empty array
    if (selected.length > 0) {
      setDisplaySelectedModes(uniq(selected));
    }
    // If selected is empty, keep current visual state unchanged
  }, [selected, allInternals]);

  /**
   * Check if a display group (button) should appear selected
   * Returns true if at least one of the internal keys for this display is selected
   * @param internals - Array of internal keys for a display group
   * @returns Whether this display group should show as selected
   */
  const isDisplaySelected = (internals: string[]) =>
    internals.some((internal) => displaySelectedModes.includes(internal));

  /**
   * Toggle selection state for a display group
   * Handles adding/removing all internal keys for a display name
   * Also determines what to emit to the parent component
   *
   * @param internals - Array of internal keys to toggle
   */
  const toggle = (internals: string[]) => {
    const currentlyOn = isDisplaySelected(internals);

    // Update visual state: add or remove all internals for this display
    const nextDisplay = currentlyOn
      ? displaySelectedModes.filter((s) => !internals.includes(s))
      : uniq([...displaySelectedModes, ...internals]);

    setDisplaySelectedModes(nextDisplay);

    // Determine what to emit to parent based on the new selection
    const nextSet = new Set(nextDisplay);

    if (nextSet.size === 0) {
      // No modes selected → emit empty array (means "no filtering")
      onChange([]);
      return;
    }

    // Check if all possible modes are selected
    const allSet = new Set(allInternals);
    const isAllSelected =
      nextSet.size === allSet.size && [...allSet].every((x) => nextSet.has(x));

    if (isAllSelected) {
      // All modes selected → emit empty array (means "no filtering, show all")
      onChange([]);
    } else {
      // Partial selection → emit the actual selected internal keys
      onChange([...nextSet]);
    }
  };

  /**
   * Select all game modes
   * Sets visual state to show all modes selected and emits empty array to parent
   */
  const selectAll = () => {
    setDisplaySelectedModes(allInternals);
    onChange([]); // Empty array means "all selected" to the parent
  };

  /**
   * Clear all selections
   * Sets visual state to show no modes selected and emits empty array to parent
   */
  const clearAll = () => {
    setDisplaySelectedModes([]); // Visual: no modes selected
    onChange([]); // API: no filtering (could mean "show all" or "show none" based on backend logic)
  };

  return (
    <div className="game-mode-filter-container">
      {/* Header button to toggle expand/collapse state */}
      <button
        type="button"
        className="game-mode-filter-component-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="game-mode-filter-component-title">Game Modes</span>
        {/* Chevron icon that rotates based on expanded state */}
        <ChevronUp
          className={`game-mode-filter-component-toggle ${
            isExpanded ? "" : "collapsed"
          }`}
        />
      </button>

      {/* Filter options grid - hidden/shown based on expanded state */}
      <div
        id="game-mode-filter-grid"
        className={`game-mode-filter-component-grid ${
          isExpanded ? "" : "hidden"
        }`}
      >
        {/* Render a button for each unique display name */}
        {options.map(({ internals, display }) => (
          <button
            key={display}
            type="button"
            className={`game-mode-filter-component-tag ${
              isDisplaySelected(internals) ? "is-selected" : ""
            }`}
            onClick={() => toggle(internals)}
          >
            <span className="game-mode-filter-component-tag-text">
              {display}
            </span>
          </button>
        ))}

        {/* Action buttons for bulk operations */}
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
