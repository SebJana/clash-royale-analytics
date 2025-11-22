import { useState, useEffect } from "react";
import { GameModeFilter } from "../gameModeFilter/gameModeFilter";
import { StartEndDateFilter } from "../startEndDateFilter/startEndDateFilter";
import { CardFilter } from "../cardFilter/cardFilter";
import type { Card, CardMeta } from "../../types/cards";
import {
  getDateRange,
  getDefaultFilterState,
  setFilterStateToLocalStorage,
} from "../../utils/filter";
import { isValidDateRange } from "../../utils/datetime";
import "./filterContainer.css";

// TODO add visualSelectedGameModes here to selectedGameModes
export type FilterState = {
  startDate: string;
  endDate: string;
  gameModes: string[];
  cards: Card[];
  includeCardFilterMode: boolean;
  timespanOption: string;
};

type FilterContainerProps = {
  gameModes: Record<string, string>;
  cards: CardMeta[];
  gameModesLoading: boolean;
  onFiltersApply: (filters: FilterState) => void;
  initialFilters?: Partial<FilterState>;
  showCardFilter?: boolean; // Optional prop to show/hide card filter
  // Optional prop to control wether the card filter works by definite inclusion (true) or closest match (false)
  includeCardFilterMode?: boolean;
  appliedFilters?: FilterState; // Current applied filters to sync UI
};

export function FilterContainer({
  gameModes,
  cards,
  gameModesLoading,
  onFiltersApply,
  initialFilters,
  showCardFilter,
  includeCardFilterMode,
  appliedFilters,
}: Readonly<FilterContainerProps>) {
  const initialDates = getDateRange();

  // Filter state management maintains two sets of state for each filter type:
  // 1. "selected" - what the user has chosen in the UI (not yet applied)
  // 2. "applied" - what is actually used for the API query
  // Use appliedFilters if available, otherwise fall back to initialFilters, then defaults
  const [selectedGameModes, setSelectedGameModes] = useState<string[]>(
    appliedFilters?.gameModes || initialFilters?.gameModes || []
  );
  const [appliedGameModes, setAppliedGameModes] = useState<string[]>(
    appliedFilters?.gameModes || initialFilters?.gameModes || []
  );

  const [selectedCards, setSelectedCards] = useState<Card[]>(
    showCardFilter ? appliedFilters?.cards || initialFilters?.cards || [] : []
  );
  const [appliedCards, setAppliedCards] = useState<Card[]>(
    showCardFilter ? appliedFilters?.cards || initialFilters?.cards || [] : []
  );

  const [selectedIncludeCardFilterMode, setSelectedIncludeCardFilterMode] =
    useState<boolean>(
      appliedFilters?.includeCardFilterMode ??
        initialFilters?.includeCardFilterMode ??
        includeCardFilterMode ??
        true
    );
  const [appliedIncludeCardFilterMode, setAppliedIncludeCardFilterMode] =
    useState<boolean>(
      appliedFilters?.includeCardFilterMode ??
        initialFilters?.includeCardFilterMode ??
        includeCardFilterMode ??
        true
    );

  const [selectedStartDate, setSelectedStartDate] = useState<string>(
    appliedFilters?.startDate || initialFilters?.startDate || initialDates.start
  );
  const [appliedStartDate, setAppliedStartDate] = useState<string>(
    appliedFilters?.startDate || initialFilters?.startDate || initialDates.start
  );

  const [selectedEndDate, setSelectedEndDate] = useState<string>(
    appliedFilters?.endDate || initialFilters?.endDate || initialDates.end
  );
  const [appliedEndDate, setAppliedEndDate] = useState<string>(
    appliedFilters?.endDate || initialFilters?.endDate || initialDates.end
  );

  const [selectedTimespanOption, setSelectedTimespanOption] = useState<string>(
    appliedFilters?.timespanOption ||
      initialFilters?.timespanOption ||
      "Last 7 days"
  );

  const [gameModesInitialized, setGameModesInitialized] = useState(false);
  const [applyButtonDisabled, setApplyButtonDisabled] = useState(true);

  // Sync UI state with applied filters when they change from parent
  useEffect(() => {
    if (appliedFilters) {
      setSelectedStartDate(appliedFilters.startDate);
      setSelectedEndDate(appliedFilters.endDate);
      setSelectedGameModes(appliedFilters.gameModes);
      setSelectedTimespanOption(appliedFilters.timespanOption);
      setSelectedIncludeCardFilterMode(appliedFilters.includeCardFilterMode);
      if (showCardFilter) {
        setSelectedCards(appliedFilters.cards);
      }

      // Also update applied state to match
      setAppliedStartDate(appliedFilters.startDate);
      setAppliedEndDate(appliedFilters.endDate);
      setAppliedGameModes(appliedFilters.gameModes);
      setAppliedIncludeCardFilterMode(appliedFilters.includeCardFilterMode);
      if (showCardFilter) {
        setAppliedCards(appliedFilters.cards);
      }
    }
  }, [appliedFilters, showCardFilter]);

  // Game mode initialization
  useEffect(() => {
    if (gameModes && !gameModesInitialized && !gameModesLoading) {
      const allGameModeKeys = Object.keys(gameModes);

      // Only initialize with all game modes if no applied filters exist
      // This prevents overriding user's applied filter selections
      if (!appliedFilters || appliedFilters.gameModes.length === 0) {
        setSelectedGameModes(allGameModeKeys);
        setAppliedGameModes(allGameModeKeys);
      }

      setGameModesInitialized(true);
    }
  }, [gameModes, gameModesInitialized, gameModesLoading, appliedFilters]);

  // Enable apply button when any selection differs from applied state
  useEffect(() => {
    const cardsChanged = showCardFilter
      ? JSON.stringify(appliedCards) !== JSON.stringify(selectedCards)
      : false;
    const cardFilterModeChanged =
      appliedIncludeCardFilterMode !== selectedIncludeCardFilterMode;

    const validDateRange = isValidDateRange(selectedStartDate, selectedEndDate);

    if (
      (appliedStartDate !== selectedStartDate ||
        appliedEndDate !== selectedEndDate ||
        JSON.stringify(appliedGameModes) !==
          JSON.stringify(selectedGameModes) ||
        cardsChanged ||
        cardFilterModeChanged) &&
      validDateRange
    ) {
      setApplyButtonDisabled(false);
    } else {
      setApplyButtonDisabled(true);
    }
  }, [
    appliedStartDate,
    appliedEndDate,
    appliedGameModes,
    appliedCards,
    appliedIncludeCardFilterMode,
    selectedStartDate,
    selectedEndDate,
    selectedGameModes,
    selectedCards,
    selectedIncludeCardFilterMode,
    showCardFilter,
  ]);

  // Apply all filters and notify parent
  const applyAllFilters = () => {
    const newFilters: FilterState = {
      startDate: selectedStartDate,
      endDate: selectedEndDate,
      gameModes: selectedGameModes,
      cards: showCardFilter ? selectedCards : [], // Only include cards if card filter is enabled
      includeCardFilterMode: selectedIncludeCardFilterMode,
      timespanOption: selectedTimespanOption,
    };

    setAppliedStartDate(selectedStartDate);
    setAppliedEndDate(selectedEndDate);
    setAppliedGameModes(selectedGameModes);
    setAppliedIncludeCardFilterMode(selectedIncludeCardFilterMode);
    if (showCardFilter) {
      setAppliedCards(selectedCards);
    }

    // Save the current state of the filter to the local Storage
    setFilterStateToLocalStorage(newFilters);

    onFiltersApply(newFilters);
  };

  // Reset clears the selection, user still has to click apply for the default to take effect
  const resetAllFilters = () => {
    const defaultFilters = getDefaultFilterState();

    setSelectedStartDate(defaultFilters.startDate);
    setSelectedEndDate(defaultFilters.endDate);
    setSelectedTimespanOption(defaultFilters.timespanOption);
    setSelectedGameModes(defaultFilters.gameModes);
    setSelectedIncludeCardFilterMode(defaultFilters.includeCardFilterMode);
    if (showCardFilter) {
      setSelectedCards(defaultFilters.cards);
    }
  };

  return (
    <div className="filter-component-container">
      <h2 className="filter-component-header">Filters</h2>
      <StartEndDateFilter
        selectedStart={selectedStartDate}
        selectedEnd={selectedEndDate}
        selectedOption={selectedTimespanOption}
        onStartChange={setSelectedStartDate}
        onEndChange={setSelectedEndDate}
        onOptionChange={setSelectedTimespanOption}
      />
      <GameModeFilter
        gameModes={gameModes}
        selected={selectedGameModes}
        onChange={setSelectedGameModes}
      />
      {showCardFilter && (
        <CardFilter
          cards={cards}
          selected={selectedCards}
          onCardsChange={setSelectedCards}
          includeCardFilterMode={selectedIncludeCardFilterMode}
          onCardFilterModeChange={setSelectedIncludeCardFilterMode}
        />
      )}
      <div className="filter-component-button-container">
        <button
          type="button"
          className="filter-component-apply-button"
          onClick={applyAllFilters}
          disabled={applyButtonDisabled}
        >
          Apply
        </button>
        <button
          type="button"
          className="filter-component-reset-button filter-component-action-button"
          onClick={resetAllFilters}
        >
          Reset
        </button>
      </div>
    </div>
  );
}
