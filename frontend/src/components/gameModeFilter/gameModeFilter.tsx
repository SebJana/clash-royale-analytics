import { useMemo, useState } from "react";
import {
  internalNamesToDisplayNames,
  internalDisplayMapToDisplayNamesList,
} from "../../utils/gameModes";
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import "./gameModeFilter.css";

type GameModeOption = {
  display: string;
  internals: string[];
};

/**
 * GameModeFilter Component
 *
 * A collapsible, searchable game mode selector. The dropdown presents friendly
 * display names, but every selection sent to the parent stays as the internal
 * name saved in the database.
 *
 * Key behaviors:
 * - Empty selection array means "all modes selected" (no filtering / no query param)
 * - Empty selection intentionally has no bonbons; bonbons only represent an explicit subset
 * - Multiple internal modes may share one display name, so they are selected and removed together
 * - Clicking a selected bonbon directly removes its display group from the selection
 */
export function GameModeFilter({
  gameModes,
  selected,
  onChange,
}: Readonly<{
  gameModes: Record<string, string>;
  selected: string[];
  onChange: (next: string[]) => void;
}>) {
  // Controls the same show/hide behavior used by the other filter sections.
  const [isFilterVisible, setIsFilterVisible] = useState(false);
  // The mode list is a separate dropdown inside the expanded filter section.
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  // Keep the search value local so typing does not affect the applied filters.
  const [searchTerm, setSearchTerm] = useState("");

  // Convert raw names from the API into the labels shown to the user.
  const gameModesMap = useMemo(
    () => internalNamesToDisplayNames(gameModes),
    [gameModes]
  );

  // Build one option for each display name. This keeps related internal names
  // (for example Ranked variants) together while the API still receives raw names.
  const options = useMemo<GameModeOption[]>(() => {
    const displayNames = internalDisplayMapToDisplayNamesList(gameModesMap);

    return displayNames
      .map((display) => ({
        display,
        internals: Array.from(gameModesMap.entries())
          .filter(([, displayName]) => displayName === display)
          .map(([internal]) => internal),
      }))
      .sort((a, b) =>
        a.display.localeCompare(b.display, undefined, { sensitivity: "base" })
      );
  }, [gameModesMap]);

  // A Set makes repeated selected-state checks cheap while rendering the list.
  const selectedSet = useMemo(() => new Set(selected), [selected]);

  // Only explicit selections become bonbons. [] means all modes, therefore no bonbons.
  const selectedOptions = useMemo(
    () =>
      options.filter((option) =>
        option.internals.some((internal) => selectedSet.has(internal))
      ),
    [options, selectedSet]
  );

  // Search both the friendly label and the internal value. The latter is useful
  // when a user sees a raw mode name in a battle response or URL.
  const filteredOptions = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLocaleLowerCase();
    if (!normalizedSearch) return options;

    return options.filter(
      ({ display, internals }) =>
        display.toLocaleLowerCase().includes(normalizedSearch) ||
        internals.some((internal) =>
          internal.toLocaleLowerCase().includes(normalizedSearch)
        )
    );
  }, [options, searchTerm]);

  // A display group is selected if at least one of its raw modes is selected.
  const isOptionSelected = (option: GameModeOption) =>
    option.internals.some((internal) => selectedSet.has(internal));

  // Toggle every raw name represented by a display option, never the display name itself.
  const toggleOption = (option: GameModeOption) => {
    if (isOptionSelected(option)) {
      onChange(selected.filter((mode) => !option.internals.includes(mode)));
      return;
    }

    onChange(Array.from(new Set([...selected, ...option.internals])));
  };

  const selectAllModes = () => {
    // Empty is intentionally the all-modes state, not an empty result set.
    onChange([]);
  };

  // Bonbons are shortcuts for removing a selected display group.
  const removeOption = (option: GameModeOption) => {
    onChange(selected.filter((mode) => !option.internals.includes(mode)));
  };

  return (
    <div className="game-mode-filter-container">
      <button
        type="button"
        className="game-mode-filter-component-header"
        onClick={() => setIsFilterVisible((visible) => !visible)}
        aria-expanded={isFilterVisible}
        aria-controls="game-mode-filter-content"
      >
        {/* Header stays left-aligned and toggles the entire filter section. */}
        <span className="game-mode-filter-component-title">Game Modes</span>
        <ChevronUp
          className={`game-mode-filter-header-toggle ${
            isFilterVisible ? "" : "collapsed"
          }`}
          aria-hidden="true"
        />
      </button>

      {isFilterVisible && (
        <div id="game-mode-filter-content" className="game-mode-filter-content">
          {selectedOptions.length > 0 && (
            <div
              className="game-mode-filter-selected"
              aria-label="Selected game modes"
            >
              {/* Clicking a bonbon removes it immediately; there is no separate delete state. */}
              {selectedOptions.map((option) => (
                <button
                  key={option.display}
                  type="button"
                  className="game-mode-filter-bonbon"
                  onClick={() => removeOption(option)}
                  aria-label={`Remove ${option.display}`}
                  title={`Remove ${option.display}`}
                >
                  {option.display}
                </button>
              ))}
            </div>
          )}

          <button
            type="button"
            className="game-mode-filter-dropdown-trigger"
            onClick={() => setIsDropdownOpen((open) => !open)}
            aria-expanded={isDropdownOpen}
            aria-controls="game-mode-filter-dropdown"
          >
            <span>
              {selectedOptions.length === 0
                ? "All game modes"
                : `${selectedOptions.length} mode${
                    selectedOptions.length === 1 ? "" : "s"
                  } selected`}
            </span>
            <ChevronDown
              className={`game-mode-filter-component-toggle ${
                isDropdownOpen ? "expanded" : ""
              }`}
              aria-hidden="true"
            />
          </button>

          {isDropdownOpen && (
            <div
              id="game-mode-filter-dropdown"
              className="game-mode-filter-dropdown"
            >
              <label className="game-mode-filter-search">
                <Search aria-hidden="true" />
                <span className="sr-only">Search game modes</span>
                <input
                  type="search"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Search game modes"
                />
              </label>

              <div
                className="game-mode-filter-options"
                role="listbox"
                aria-label="Game modes"
              >
                {/* Resetting to [] is how the API knows to include every saved game mode. */}
                <button
                  type="button"
                  className={`game-mode-filter-option ${
                    selected.length === 0 ? "is-selected" : ""
                  }`}
                  onClick={selectAllModes}
                  role="option"
                  aria-selected={selected.length === 0}
                >
                  All game modes
                </button>
                {filteredOptions.map((option) => (
                  <button
                    key={option.display}
                    type="button"
                    className={`game-mode-filter-option ${
                      isOptionSelected(option) ? "is-selected" : ""
                    }`}
                    onClick={() => toggleOption(option)}
                    role="option"
                    aria-selected={isOptionSelected(option)}
                  >
                    {option.display}
                  </button>
                ))}
              </div>

              {filteredOptions.length === 0 && (
                <p className="game-mode-filter-empty">No game modes found.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
