import { useCards } from "../../hooks/useCards";
import { useParams } from "react-router-dom";
import { useDeckStats } from "../../hooks/useDeckStats";
import { DeckComponent } from "../../components/deck/deck";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { round } from "../../utils/round";
import { pluralize } from "../../utils/plural";
import { getCurrentFilterState } from "../../utils/filter";
import { datetimeToLocale } from "../../utils/datetime";
import { useEffect, useState } from "react";
import { StatCard } from "../../components/statCard/statCard";
import { ScrollToTopButton } from "../../components/scrollToTop/scrollToTop";
import { FilterContainer } from "../../components/filterContainer/filterContainer";
import type { FilterState } from "../../components/filterContainer/filterContainer";
import { SortByContainer } from "../../components/sortByContainer/sortByContainer";
import type { Card } from "../../types/cards";
import type { Deck } from "../../types/deckStats";
import "./decks.css";

// Helper type to rate/score the decks when using the card filter match mode
type DeckWithMatchScore = Deck & {
  matchPercentage: number;
  matchCount: number;
};

// Type for deck sorting that includes actual Deck fields and computed fields
type DeckSortFields = {
  count: number; // Direct field from Deck (battles)
  wins: number; // Direct field from Deck
  winRate: number; // Direct field from Deck
  usageRate: number; // Computed field
  lastSeen: string; // Direct field from Deck
};

function calculateAndFormatUsageRate(
  battleCount: number,
  totalBattles: number
) {
  const usageRate = (battleCount / totalBattles) * 100; // In percent
  const roundedUsageRate = round(usageRate, 1);
  return `${roundedUsageRate}%`;
}

// TODO add same error handling for all pages if no data is found or the tag is invalid
export default function PlayerDecks() {
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
    useState<keyof DeckSortFields>("count"); // Default: sort by battles (most relevant)
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
  const handleSortChange = (nextSortOption: keyof DeckSortFields) => {
    if (nextSortOption === selectedSortOption) {
      // Same option clicked - toggle sort direction (ascending ↔ descending)
      setSortAscending(!sortAscending);
    } else {
      // Different option selected - change sort field and reset to descending (most useful default)
      setSelectedSortOption(nextSortOption);
      setSortAscending(false);
    }
  };

  // Available sort options for decks
  const sortOptions: (keyof DeckSortFields)[] = [
    "count",
    "wins",
    "winRate",
    "usageRate",
    "lastSeen",
  ];

  // Deck statistics API call
  // Fetch deck statistics only when game modes are properly initialized
  // Uses applied filter values (not selected ones) to ensure query stability
  // Passes null for game modes to disable the query until gameModesInitialized is true
  const {
    data: deckStats,
    isLoading: decksLoading,
    isError: isDecksError,
    error: decksError,
  } = useDeckStats(
    playerTag,
    appliedFilters.startDate,
    appliedFilters.endDate,
    gameModesInitialized ? appliedFilters.gameModes : null // Use applied filters for the query
  );

  // Helper function to check if a deck contains a specific card
  const deckContainsCard = (deck: Deck, appliedCard: Card) => {
    return deck.deck?.some(
      (deckCard) =>
        deckCard.id === appliedCard.id &&
        (deckCard.evolutionLevel ?? 0) === (appliedCard.evolutionLevel ?? 0)
    );
  };

  // Helper function to calculate match percentage for a deck
  const calculateMatchPercentage = (deck: Deck) => {
    const matchingCards = calculateMatchCount(deck);
    return (matchingCards / appliedFilters.cards.length) * 100;
  };

  // Helper function to calculate amount of matched cards for a deck
  const calculateMatchCount = (deck: Deck) => {
    const matchingCards = appliedFilters.cards.filter((appliedCard) =>
      deckContainsCard(deck, appliedCard)
    );
    return matchingCards.length;
  };

  // Helper function to sort decks based on selected sort option
  // Creates a new sorted array without mutating the original deck statistics
  const sortDecks = (decksToSort: Deck[]): Deck[] => {
    return [...decksToSort].sort((a, b) => {
      let valueA: number | string;
      let valueB: number | string;

      if (selectedSortOption === "usageRate") {
        // Special case for computed field - calculate usage rate percentage on-the-fly
        // Usage rate = (deck battles / total battles in this filtered set) * 100
        const totalBattlesForSort = decksToSort.reduce(
          (sum, deck) => sum + deck.count,
          0
        );
        valueA = (a.count / totalBattlesForSort) * 100;
        valueB = (b.count / totalBattlesForSort) * 100;
      } else {
        // Direct field access using bracket notation
        // Works for: count (battles), wins, winRate, lastSeen
        // TypeScript ensures selectedSortOption is a valid key of DeckSortFields
        valueA = a[selectedSortOption];
        valueB = b[selectedSortOption];
      }

      // Handle string comparison (specifically for lastSeen ISO date strings)
      if (typeof valueA === "string" && typeof valueB === "string") {
        const comparison = valueA.localeCompare(valueB);
        return sortAscending ? comparison : -comparison;
      }

      // Handle numeric comparison for all other fields (count, wins, winRate, usageRate)
      const numA = Number(valueA);
      const numB = Number(valueB);

      // Sort direction: ascending (low to high) or descending (high to low)
      // Default is descending to show highest values first (most battles, highest win rates, etc.)
      return sortAscending ? numA - numB : numB - numA;
    });
  };

  // Filter and sort decks based on applied cards with two modes:
  // 1) Include mode: decks HAVE to include ALL selected cards
  // 2) Match mode: decks are scored by percentage of selected cards they contain and sorted by match percentage
  const filteredDecks = (() => {
    if (!deckStats?.deck_statistics.decks) return [];

    const allDecks = deckStats.deck_statistics.decks;

    // If no cards are applied as filters, show all decks with sorting applied
    if (!appliedFilters.cards || appliedFilters.cards.length === 0) {
      // Apply user-selected sorting to all available decks
      return sortDecks(allDecks);
    }

    if (appliedFilters.includeCardFilterMode === true) {
      // Include mode: deck must contain ALL selected cards (strict filtering)
      const filteredDecks = allDecks.filter((deck) => {
        return appliedFilters.cards.every((appliedCard) =>
          deckContainsCard(deck, appliedCard)
        );
      });

      // Apply user-selected sorting to the filtered decks
      return sortDecks(filteredDecks);
    } else {
      // Match mode: calculate match percentage and sort by it
      const decksWithMatchScore = allDecks.map((deck) => {
        const matchPercentage = calculateMatchPercentage(deck);
        const matchCount = calculateMatchCount(deck);
        return {
          ...deck,
          matchPercentage,
          matchCount,
        };
      });

      // Filter out decks with 0% match and sort by match percentage (highest first)
      return decksWithMatchScore
        .filter((deck) => deck.matchPercentage > 0)
        .sort((a, b) => b.matchPercentage - a.matchPercentage);
    }
    // Either return the Deck (include mode) or the Deck and its score (match mode)
  })() as (Deck | DeckWithMatchScore)[];

  // Create cache key from applied filters for loading state dependency
  const modesKey = appliedFilters.gameModes.join("|");

  // Loading state management
  // Determines when to show loading spinner vs content
  // Uses a custom hook that tracks multiple loading states and prevents flickering
  // NOTE: Cards filter is frontend-only, so not included in resetDependency
  const { isInitialLoad } = usePageLoadingState({
    loadingStates: [decksLoading, cardsLoading, gameModesLoading],
    errorStates: [isDecksError, isCardsError, isGameModesError],
    hasData: () => Boolean(filteredDecks && filteredDecks.length > 0),
    // Reset dependency ensures loading state recalculates when any backend filter changes
    resetDependency: `${playerTag}}-${appliedFilters.startDate}-${appliedFilters.endDate}-${modesKey}`,
  });

  // Calculate totals based on filtered decks
  let totalBattles = 0;
  let totalWins = 0;
  for (const deck of filteredDecks) {
    totalBattles += deck.count;
    totalWins += deck.wins;
  }
  const totalDecks = filteredDecks.length;

  return (
    <div className="decks-page">
      <div className="decks-content">
        {isDecksError && <div>Error: {decksError?.message}</div>}
        {isCardsError && <div>Error: {cardsError?.message}</div>}
        {isGameModesError && <div>Error: {gameModesError?.message}</div>}

        {/* Loading State - Shows during initial load, cards loading, decks loading, or game mode loading */}
        {/* The loading spinner prevents users from seeing incomplete data during the initialization process */}
        {(isInitialLoad ||
          decksLoading ||
          cardsLoading ||
          gameModesLoading) && (
          <div>
            <CircularProgress className="decks-loading-spinner" />
            <p>Loading decks...</p>
          </div>
        )}
        {/* Loaded State - Show decks when all data is available and no errors occurred */}
        {!isDecksError && !isGameModesError && !isInitialLoad && (
          <>
            {/* FilterContainer component */}
            <FilterContainer
              gameModes={gameModes || {}}
              cards={cards || []}
              gameModesLoading={gameModesLoading}
              onFiltersApply={handleFiltersApply}
              showCardFilter={true}
              appliedFilters={appliedFilters}
              initialFilters={getCurrentFilterState()}
            />

            <SortByContainer<DeckSortFields>
              options={sortOptions}
              selectedOption={selectedSortOption}
              ascending={sortAscending}
              // Only enable deck sorting in Include mode (when cards are filtered/selected with include mode)
              disableSort={
                appliedFilters.cards.length > 0 &&
                !appliedFilters.includeCardFilterMode
              }
              onSelectedOptionChange={handleSortChange}
            />

            {/* Show decks if there is any data to display */}
            {filteredDecks && filteredDecks.length > 0 && (
              <div className="decks-stats">
                <h2>Overall Performance</h2>
                <div className="decks-general-stats">
                  <StatCard
                    label={pluralize(totalBattles, "Battle", "Battles")}
                    value={totalBattles}
                  />
                  <StatCard
                    label={pluralize(totalDecks, "Deck", "Decks")}
                    value={totalDecks}
                  />
                  <StatCard
                    label={pluralize(totalWins, "Win", "Wins")}
                    value={totalWins}
                  />
                  <StatCard
                    label="Win Rate"
                    value={`${round((totalWins / totalBattles) * 100, 1)}%`}
                  />
                </div>
                {filteredDecks.map((d) => (
                  <div
                    className="decks-deck-row"
                    // Unique deck id of all cards in the deck
                    key={`${d.deck?.map((c) => c.id).join(";")}`}
                  >
                    {/* TODO add a deck name, by using the top x elixir cards 
                      or by using the win condition and the most expensive card */}
                    <div className="deck-section">
                      {/* Show match percentage only in match mode */}
                      {!appliedFilters.includeCardFilterMode &&
                        appliedFilters.cards.length > 0 &&
                        "matchPercentage" in d && (
                          <div className="decks-card-match-header">
                            <span className="decks-card-match-value">{`${round(
                              d.matchPercentage,
                              1
                            )}% (${d.matchCount} matching ${pluralize(
                              d.matchCount,
                              "Card",
                              "Cards"
                            )})`}</span>
                            <span className="decks-card-match-label">
                              Card Match
                            </span>
                          </div>
                        )}
                      <DeckComponent deck={d.deck} cards={cards ?? []} />
                    </div>
                    <div className="deck-stats-container">
                      <StatCard
                        label={pluralize(d.count, "Battle", "Battles")}
                        value={d.count}
                      />
                      <StatCard
                        label={pluralize(d.wins, "Win", "Wins")}
                        value={d.wins}
                      />
                      <StatCard
                        label="Win Rate"
                        value={`${round(d.winRate, 1)}%`}
                      />
                      <StatCard
                        label="Usage Rate"
                        value={calculateAndFormatUsageRate(
                          d.count,
                          totalBattles
                        )}
                      />
                      <StatCard
                        label={pluralize(
                          d.modes.length,
                          "Game Mode",
                          "Game Modes"
                        )}
                        value={d.modes.length}
                      />
                      <StatCard
                        label="Last Seen"
                        value={datetimeToLocale(d.lastSeen)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
            <ScrollToTopButton />

            {/* Show message when no decks are found and not still loading */}
            {(!filteredDecks || filteredDecks.length === 0) &&
              !decksLoading &&
              !gameModesLoading &&
              !cardsLoading && (
                <div className="no-decks-message">
                  <p>No decks found with the current filters applied</p>
                </div>
              )}
          </>
        )}
      </div>
    </div>
  );
}
