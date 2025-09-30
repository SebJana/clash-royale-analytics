import { useCards } from "../../hooks/useCards";
import { useParams } from "react-router-dom";
import { useCardStats } from "../../hooks/useCardStats";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { round } from "../../utils/round";
import { pluralize } from "../../utils/plural";
import { useEffect, useState } from "react";
import { GameModeFilter } from "../../components/gameModeFilter/gameModeFilter";
import { StartEndDateFilter } from "../../components/startEndDateFilter/startEndDateFilter";
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

  // Helper function to format date for input fields (YYYY-MM-DD format)
  const formatDateForInput = (date: Date): string => {
    return date.toISOString().slice(0, 10); // Format as YYYY-MM-DD
  };

  // Initialize with last 7 days as default date range
  // This provides a slim default range that shows recent deck data immediately
  // NOTE: Whenever this initialization changes, also update the "pre-chosen"
  // selectedTimespanOption of the StartEndDateFilter
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
  // 2. "applied" - what is actually used for the API query (in case of cards for the frontend filter)
  // This allows users to configure multiple filters before applying them all at once to reduce API calls and loading times

  // Game mode filters
  const [selectedGameModes, setSelectedGameModes] = useState<string[]>([]); // UI selection
  const [appliedGameModes, setAppliedGameModes] = useState<string[]>([]); // Query parameters

  // Date range filters
  const [selectedStartDate, setSelectedStartDate] = useState<string>(
    initialDates.start // Initialize with last 7 days start
  );
  const [appliedStartDate, setAppliedStartDate] = useState<string>(
    initialDates.start // Initialize applied state so query runs immediately
  );

  const [selectedEndDate, setSelectedEndDate] = useState<string>(
    initialDates.end // Initialize with today
  );
  const [appliedEndDate, setAppliedEndDate] = useState<string>(
    initialDates.end // Initialize applied state so query runs immediately
  );

  // Timespan option selection (persists which preset was chosen)
  // For all the other filters, the selected/applied options are the chosen preset
  const [selectedTimespanOption, setSelectedTimespanOption] =
    useState<string>("Last 7 days");

  // Prevents double API calls during initialization, because filter and query need to be built on API Game Modes Data
  const [gameModesInitialized, setGameModesInitialized] = useState(false);

  // Upon loading no configuration is changed --> disable apply button
  const [applyButtonDisabled, setApplyButtonDisabled] = useState(true);

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
      setSelectedGameModes(allGameModeKeys); // Set UI selection
      setAppliedGameModes(allGameModeKeys); // Set query parameters immediately
      setGameModesInitialized(true);
    }
  }, [gameModes, gameModesInitialized, gameModesLoading]);

  // Only enable apply button, when any selection differs from the current applied state
  useEffect(() => {
    // Simple comparison using JSON.stringify for arrays
    if (
      appliedStartDate !== selectedStartDate ||
      appliedEndDate !== selectedEndDate ||
      JSON.stringify(appliedGameModes) !== JSON.stringify(selectedGameModes)
    ) {
      setApplyButtonDisabled(false); // Button enabled
    } else {
      setApplyButtonDisabled(true); // Button disabled
    }
  }, [
    appliedStartDate,
    appliedEndDate,
    appliedGameModes,
    selectedStartDate,
    selectedEndDate,
    selectedGameModes,
  ]);

  // Filter application
  // Transfers all selected filter values to applied filter state
  // This triggers the deck statistics query with the new parameters
  const applyAllFilters = () => {
    setAppliedStartDate(selectedStartDate);
    setAppliedEndDate(selectedEndDate);
    setAppliedGameModes(selectedGameModes);
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
    appliedStartDate,
    appliedEndDate,
    gameModesInitialized ? appliedGameModes : null // Use applied filters for the query
  );

  // Create cache key from applied filters for loading state dependency
  const modesKey = appliedGameModes.join("|");

  // Loading state management
  // Determines when to show loading spinner vs content
  // Uses a custom hook that tracks multiple loading states and prevents flickering
  const { isInitialLoad } = usePageLoadingState({
    loadingStates: [cardsLoading, cardStatsLoading, gameModesLoading],
    errorStates: [isCardStatsError, isCardsError, isGameModesError],
    hasData: () =>
      Boolean(cardStats && cardStats.card_statistics.cards.length > 0),
    // Reset dependency ensures loading state recalculates when any backend filter changes
    resetDependency: `${playerTag}-${appliedStartDate}-${appliedEndDate}-${modesKey}`,
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
            <div className="cards-filter-container">
              <h2 className="cards-filter-header">Filters</h2>
              <StartEndDateFilter
                selectedStart={selectedStartDate}
                selectedEnd={selectedEndDate}
                selectedOption={selectedTimespanOption}
                onStartChange={setSelectedStartDate}
                onEndChange={setSelectedEndDate}
                onOptionChange={setSelectedTimespanOption}
              />
              <GameModeFilter
                gameModes={gameModes ?? {}}
                selected={selectedGameModes}
                onChange={setSelectedGameModes}
              />
              <button
                type="button"
                className="cards-apply-filters-button"
                onClick={applyAllFilters}
                disabled={applyButtonDisabled}
              >
                Apply
              </button>
            </div>

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
