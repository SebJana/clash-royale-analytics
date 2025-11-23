import { useCards } from "../../hooks/useCards";
import { useParams } from "react-router-dom";
import { useCardStats } from "../../hooks/useCardStats";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { round } from "../../utils/number";
import { pluralize } from "../../utils/plural";
import { getCurrentFilterState } from "../../utils/filter";
import { useEffect, useState } from "react";
import { ScrollToTopButton } from "../../components/scrollToTop/scrollToTop";
import { FilterContainer } from "../../components/filterContainer/filterContainer";
import type { FilterState } from "../../components/filterContainer/filterContainer";
import { SortByContainer } from "../../components/sortByContainer/sortByContainer";
import { CardComponent } from "../../components/card/card";
import type { CardStats } from "../../types/cardStats";
import "./cards.css";

function calculateAndFormatUsageRate(
  battleCount: number,
  totalBattles: number
) {
  const usageRate = (battleCount / totalBattles) * 100; // In percent
  const roundedUsageRate = round(usageRate, 1);
  return `${roundedUsageRate}%`;
}

// Type for card sorting that includes actual CardStat fields and computed fields
type CardSortFields = {
  usage: number; // Direct field from CardStat (battles)
  wins: number; // Direct field from CardStat
  winRate: number; // Direct field from CardStat
  usageRate: number; // Computed field
};

export default function PlayerCards() {
  const { playerTag = "" } = useParams();

  // Filter state management maintains two sets of state for each filter type:
  // 1. "selected" - what the user has chosen in the UI (not yet applied)
  // 2. "applied" - what is actually used for the API query (in case of cards for the frontend filter)
  // This allows users to configure multiple filters before applying them all at once to reduce API calls and loading times

  // State to store applied filters from FilterContainer
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(
    getCurrentFilterState()
  );

  // Prevents double API calls during initialization, because filter and query need to be built on API Game Modes Data
  const [gameModesInitialized, setGameModesInitialized] = useState(false);

  // Sort state management
  // Tracks which field to sort by and the sort direction
  const [selectedSortOption, setSelectedSortOption] =
    useState<keyof CardSortFields>("usage"); // Default: sort by battles (most relevant)
  const [sortAscending, setSortAscending] = useState(false); // Default to descending (highest values first)

  const {
    data: cards,
    isLoading: cardsLoading,
    isError: isCardsError,
    error: cardsError,
  } = useCards();

  const {
    data: gameModes,
    isLoading: gameModesLoading,
    isError: isGameModesError,
    error: gameModesError,
  } = useGameModes();

  // Game mode initialization
  // Initialize selected game modes once when game modes are loaded
  // This prevents double API calls by ensuring deck stats only load after game modes are ready
  useEffect(() => {
    if (gameModes && !gameModesInitialized && !gameModesLoading) {
      // Auto-select all game modes when they first become available
      // This provides a good default that shows all available data
      const allGameModeKeys = Object.keys(gameModes);

      // Only initialize if no game modes are already selected to avoid overriding user selections
      setAppliedFilters((prev) => ({
        ...prev,
        gameModes:
          prev.gameModes.length === 0 ? allGameModeKeys : prev.gameModes,
      }));
      setGameModesInitialized(true);
    }
  }, [gameModes, gameModesInitialized, gameModesLoading]);

  const handleFiltersApply = (filters: FilterState) => {
    setAppliedFilters(filters);
    // The API queries will automatically re-run when appliedFilters changes
  };

  // Sort handler function - manages sort option and direction state
  // Clicking same option toggles direction, clicking different option resets to descending
  const handleSortChange = (nextSortOption: keyof CardSortFields) => {
    if (nextSortOption === selectedSortOption) {
      // Same option clicked - toggle sort direction (ascending ↔ descending)
      setSortAscending(!sortAscending);
    } else {
      // Different option selected - change sort field and reset to descending (most useful default)
      setSelectedSortOption(nextSortOption);
      setSortAscending(false);
    }
  };

  // Available sort options for cards
  const sortOptions: (keyof CardSortFields)[] = [
    "usage",
    "wins",
    "winRate",
    "usageRate",
  ];

  // Helper function to sort cards based on selected sort option
  // Creates a new sorted array without mutating the original card statistics
  const sortCards = (
    cardsToSort: CardStats["card_statistics"]["cards"]
  ): CardStats["card_statistics"]["cards"] => {
    return [...cardsToSort].sort((a, b) => {
      let valueA: number | string;
      let valueB: number | string;

      if (selectedSortOption === "usageRate") {
        // Special case for computed field - calculate usage rate percentage on-the-fly
        // Usage rate = (card battles / total battles) * 100
        const totalBattles = cardStats?.card_statistics.totalBattles ?? 0;
        valueA = (a.usage / totalBattles) * 100;
        valueB = (b.usage / totalBattles) * 100;
      } else {
        // Direct field access using bracket notation
        // Works for: usage (battles), wins, winRate
        // TypeScript ensures selectedSortOption is a valid key of CardSortFields
        valueA = a[selectedSortOption];
        valueB = b[selectedSortOption];
      }

      // Convert to numbers for consistent comparison (all card stats are numeric)
      const numA = Number(valueA);
      const numB = Number(valueB);

      // Sort direction: ascending (low to high) or descending (high to low)
      // Default is descending to show highest values first (most used cards, highest win rates, etc.)
      return sortAscending ? numA - numB : numB - numA;
    });
  };

  // Card statistics API call
  // Fetch card statistics only when game modes are properly initialized
  // Uses applied filter values (not selected ones) to ensure query stability
  // Passes null for game modes to disable the query until gameModesInitialized is true
  const {
    data: cardStats,
    isLoading: cardStatsLoading,
    isError: isCardStatsError,
    error: cardStatsError,
  } = useCardStats(
    playerTag,
    appliedFilters.startDate,
    appliedFilters.endDate,
    gameModesInitialized ? appliedFilters.gameModes : null // Use applied filters for the query
  );

  // Create cache key from applied filters for loading state dependency
  const modesKey = appliedFilters.gameModes.join("|");

  // Loading state management
  // Determines when to show loading spinner vs content
  // Uses a custom hook that tracks multiple loading states and prevents flickering
  const { isInitialLoad } = usePageLoadingState({
    loadingStates: [cardsLoading, cardStatsLoading, gameModesLoading],
    errorStates: [isCardStatsError, isCardsError, isGameModesError],
    hasData: () =>
      Boolean(cardStats && cardStats.card_statistics.cards.length > 0),
    // Reset dependency ensures loading state recalculates when any backend filter changes
    resetDependency: `${playerTag}-${appliedFilters.startDate}-${appliedFilters.endDate}-${modesKey}`,
  });

  const totalBattles = cardStats?.card_statistics.totalBattles ?? 0;

  // Apply sorting to card statistics for display
  // Only sort if card data exists, otherwise return empty array
  const sortedCards = cardStats?.card_statistics.cards
    ? sortCards(cardStats.card_statistics.cards)
    : [];

  return (
    <div className="cards-page">
      <div className="cards-content">
        {isCardStatsError && <div>Error: {cardStatsError?.message}</div>}
        {isCardsError && <div>Error: {cardsError?.message}</div>}
        {isGameModesError && <div>Error: {gameModesError?.message}</div>}

        {/* Loading State - Shows during initial load, cards loading, card stats loading, or game mode loading */}
        {/* The loading spinner prevents users from seeing incomplete data during the initialization process */}
        {(isInitialLoad ||
          cardsLoading ||
          cardStatsLoading ||
          gameModesLoading) && (
          <div>
            <CircularProgress className="cards-loading-spinner" />
            <p>Loading cards...</p>
          </div>
        )}
        {/* Loaded State - Show decks when all data is available and no errors occurred */}
        {!isCardStatsError && !isGameModesError && !isInitialLoad && (
          <>
            {/* FilterContainer component */}
            <FilterContainer
              gameModes={gameModes || {}}
              cards={cards || []}
              gameModesLoading={gameModesLoading}
              onFiltersApply={handleFiltersApply}
              showCardFilter={false}
              appliedFilters={appliedFilters}
              initialFilters={getCurrentFilterState()}
            />

            <SortByContainer<CardSortFields>
              options={sortOptions}
              selectedOption={selectedSortOption}
              ascending={sortAscending}
              onSelectedOptionChange={handleSortChange}
            />

            {/* Show cards if there is any data to display */}
            {sortedCards.length > 0 && (
              <div className="cards-grid">
                {sortedCards.map((c) => (
                  <div
                    className="card-item"
                    key={`${c.card.id}-${c.card.evolutionLevel}`}
                  >
                    <div className="card-item-visual">
                      <CardComponent
                        card={c.card}
                        cards={cards ?? []}
                        showTooltip={false}
                      />
                    </div>
                    <div className="card-item-stats">
                      <div className="card-item-stat">
                        <span className="card-stat-value">{c.usage}</span>
                        <span className="card-stat-label">
                          {pluralize(c.usage, "Battle", "Battles")}
                        </span>
                      </div>
                      <div className="card-item-stat">
                        <span className="card-stat-value">{c.wins}</span>
                        <span className="card-stat-label">
                          {pluralize(c.wins, "Win", "Wins")}
                        </span>
                      </div>
                      <div className="card-item-stat">
                        <span className="card-stat-value">
                          {round(c.winRate, 1)}%
                        </span>
                        <span className="card-stat-label">Win Rate</span>
                      </div>
                      <div className="card-item-stat">
                        <span className="card-stat-value">
                          {calculateAndFormatUsageRate(c.usage, totalBattles)}
                        </span>
                        <span className="card-stat-label">Usage Rate</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <ScrollToTopButton />

            {/* Show message when no cards are found and not still loading */}
            {(!cardStats || sortedCards.length === 0) &&
              !cardsLoading &&
              !gameModesLoading &&
              !cardsLoading && (
                <div className="no-cards-message">
                  <p>No cards found with the current filters applied</p>
                </div>
              )}
          </>
        )}
      </div>
    </div>
  );
}
