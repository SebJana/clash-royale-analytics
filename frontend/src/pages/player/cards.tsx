import { useCards } from "../../hooks/useCards";
import { useParams } from "react-router-dom";
import { useCardStats } from "../../hooks/useCardStats";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { round } from "../../utils/round";
import { pluralize } from "../../utils/plural";
import { getCurrentFilterState } from "../../utils/filter";
import { useEffect, useState } from "react";
import { FilterContainer } from "../../components/filterContainer/filterContainer";
import type { FilterState } from "../../components/filterContainer/filterContainer";
import { CardComponent } from "../../components/card/card";
import "./cards.css";

function calculateAndFormatUsageRate(
  battleCount: number,
  totalBattles: number
) {
  const usageRate = (battleCount / totalBattles) * 100; // In percent
  const roundedUsageRate = round(usageRate, 1);
  return `${roundedUsageRate}%`;
}

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
    console.log("Filters applied:", filters);
    // The API queries will automatically re-run when appliedFilters changes
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

            {/* Show cards if there is any data to display */}
            {cardStats && (
              <div className="cards-grid">
                {/* TODO potentially(?) supply sort by options (battles, wins, win rate, usage rate) */}
                {cardStats.card_statistics.cards.map((c) => (
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

            {/* Show message when no cards are found and not still loading */}
            {!cardStats &&
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
