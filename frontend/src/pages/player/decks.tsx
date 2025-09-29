import { useCards } from "../../hooks/useCards";
import { useParams } from "react-router-dom";
import { useDeckStats } from "../../hooks/useDeckStats";
import { DeckComponent } from "../../components/deck/deck";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { round } from "../../utils/round";
import { pluralize } from "../../utils/plural";
import { datetimeToLocale } from "../../utils/datetime";
import { useEffect, useState } from "react";
import { StatCard } from "../../components/statCard/statCard";
import { GameModeFilter } from "../../components/gameModeFilter/gameModeFilter";
import { StartEndDateFilter } from "../../components/startEndDateFilter/startEndDateFilter";
import { CardFilter } from "../../components/cardFilter/cardFilter";
import "./decks.css";
import type { Card } from "../../types/cards";

function calculateAndFormatUsageRate(
  battleCount: number,
  totalBattles: number
) {
  const usageRate = (battleCount / totalBattles) * 100; // In percent
  const roundedUsageRate = round(usageRate, 1);
  return `${roundedUsageRate}%`;
}

export default function PlayerDecks() {
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

  // Cards filter
  const [selectedCards, setSelectedCards] = useState<Card[]>([]);
  const [appliedCards, setAppliedCards] = useState<Card[]>([]);

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

  // Filter application
  // Transfers all selected filter values to applied filter state
  // This triggers the deck statistics query with the new parameters
  const applyAllFilters = () => {
    setAppliedStartDate(selectedStartDate);
    setAppliedEndDate(selectedEndDate);
    setAppliedGameModes(selectedGameModes);
    setAppliedCards(selectedCards);
  };

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
    appliedStartDate,
    appliedEndDate,
    gameModesInitialized ? appliedGameModes : null // Use applied filters for the query
  );

  // Filter decks based on applied cards
  const filteredDecks =
    deckStats?.deck_statistics.decks?.filter((deck) => {
      // If no cards are applied as filters, show all decks
      if (!appliedCards || appliedCards.length === 0) {
        return true;
      }

      // Check if the deck contains all applied cards (matching both id and evolutionLevel)
      return appliedCards.every((appliedCard) =>
        deck.deck?.some(
          (deckCard) =>
            deckCard.id === appliedCard.id &&
            // Non-evolution cards don't have that field, but need to match too
            (deckCard.evolutionLevel ?? 0) === (appliedCard.evolutionLevel ?? 0)
        )
      );
    }) ?? [];

  // Create cache key from applied filters for loading state dependency
  const modesKey = appliedGameModes.join("|");

  // Loading state management
  // Determines when to show loading spinner vs content
  // Uses a custom hook that tracks multiple loading states and prevents flickering
  // NOTE: Cards filter is frontend-only, so not included in resetDependency
  const { isInitialLoad } = usePageLoadingState({
    loadingStates: [decksLoading, cardsLoading, gameModesLoading],
    errorStates: [isDecksError, isCardsError, isGameModesError],
    hasData: () => Boolean(filteredDecks && filteredDecks.length > 0),
    // Reset dependency ensures loading state recalculates when any backend filter changes
    resetDependency: `${playerTag}}-${appliedStartDate}-${appliedEndDate}-${modesKey}`,
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
            <div className="decks-filter-container">
              <h2 className="decks-filter-header">Filters</h2>
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
              <CardFilter
                cards={cards ?? []}
                selected={selectedCards}
                onChange={setSelectedCards}
              />
              {/* TODO only enable Apply Button when any selectedValue changed */}
              <button
                type="button"
                className="decks-apply-filters-button"
                onClick={applyAllFilters}
              >
                Apply
              </button>
            </div>

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
