import { useState, useEffect } from "react";
import { GameModeFilter } from "../gameModeFilter/gameModeFilter";
import { StartEndDateFilter } from "../startEndDateFilter/startEndDateFilter";
import { CardFilter } from "../cardFilter/cardFilter";
import type { Card, CardMeta } from "../../types/cards";
import "./filter.css";

export type FilterState = {
  startDate: string;
  endDate: string;
  gameModes: string[];
  cards: Card[];
  timespanOption: string;
};

type FilterContainerProps = {
  gameModes: Record<string, string>;
  cards: CardMeta[];
  gameModesLoading: boolean;
  onFiltersApply: (filters: FilterState) => void;
  initialFilters?: Partial<FilterState>;
  showCardFilter?: boolean; // Optional prop to show/hide card filter
  appliedFilters?: FilterState; // Current applied filters to sync UI
};

export function FilterContainer({
  gameModes,
  cards,
  gameModesLoading,
  onFiltersApply,
  initialFilters,
  showCardFilter,
  appliedFilters,
}: Readonly<FilterContainerProps>) {
  // Helper function to format date for input fields (YYYY-MM-DD format)
  const formatDateForInput = (date: Date): string => {
    return date.toISOString().slice(0, 10);
  };

  // Initialize with last 7 days as default date range
  const getInitialDates = () => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);
    return {
      start: formatDateForInput(startDate),
      end: formatDateForInput(endDate),
    };
  };

  const initialDates = getInitialDates();

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
      if (showCardFilter) {
        setSelectedCards(appliedFilters.cards);
      }

      // Also update applied state to match
      setAppliedStartDate(appliedFilters.startDate);
      setAppliedEndDate(appliedFilters.endDate);
      setAppliedGameModes(appliedFilters.gameModes);
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

    if (
      appliedStartDate !== selectedStartDate ||
      appliedEndDate !== selectedEndDate ||
      JSON.stringify(appliedGameModes) !== JSON.stringify(selectedGameModes) ||
      cardsChanged
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
    selectedStartDate,
    selectedEndDate,
    selectedGameModes,
    selectedCards,
    showCardFilter,
  ]);

  // Apply all filters and notify parent
  const applyAllFilters = () => {
    const newFilters: FilterState = {
      startDate: selectedStartDate,
      endDate: selectedEndDate,
      gameModes: selectedGameModes,
      cards: showCardFilter ? selectedCards : [], // Only include cards if card filter is enabled
      timespanOption: selectedTimespanOption,
    };

    setAppliedStartDate(selectedStartDate);
    setAppliedEndDate(selectedEndDate);
    setAppliedGameModes(selectedGameModes);
    if (showCardFilter) {
      setAppliedCards(selectedCards);
    }

    onFiltersApply(newFilters);
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
          onChange={setSelectedCards}
        />
      )}
      <button
        type="button"
        className="filter-component-apply-button"
        onClick={applyAllFilters}
        disabled={applyButtonDisabled}
      >
        Apply
      </button>
    </div>
  );
}
