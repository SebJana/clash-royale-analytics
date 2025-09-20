import { useCards } from "../../hooks/useCards";
import { useParams } from "react-router-dom";
import { useDeckStats } from "../../hooks/useDeckStats";
import { DeckComponent } from "../../components/deck/deck";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { useEffect, useState } from "react";
import { GameModeFilter } from "../../components/gameModeFilter/gameModeFilter";
import "./decks.css";

export default function PlayerDecks() {
  const { playerTag = "" } = useParams();
  // Start with empty array, will be populated once game modes are loaded
  const [selectedGameModes, setSelectedGameModes] = useState<string[]>([]);
  // Applied filters that are actually used for the query
  const [appliedGameModes, setAppliedGameModes] = useState<string[]>([]);
  // Track if the game modes selection was initialized to prevent double loading
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

  // Initialize selected game modes once when game modes are loaded
  // This prevents the double-load by ensuring deck stats only load after game modes are ready
  useEffect(() => {
    if (gameModes && !gameModesInitialized && !gameModesLoading) {
      // Auto-select all game modes when they first become available
      const allGameModeKeys = Object.keys(gameModes);
      setSelectedGameModes(allGameModeKeys);
      setAppliedGameModes(allGameModeKeys); // Also initialize applied filters
      setGameModesInitialized(true);
    }
  }, [gameModes, gameModesInitialized, gameModesLoading]);

  // Function to apply the currently selected filters
  const applyAllFilters = () => {
    setAppliedGameModes(selectedGameModes);
  };

  // Fetch deck statistics only when game modes are properly initialized
  // Passes null to disable the query until gameModesInitialized is true
  const {
    data: deckStats,
    isLoading: decksLoading,
    isError: isDecksError,
    error: decksError,
  } = useDeckStats(
    playerTag,
    "2025-01-01",
    "2025-10-01",
    gameModesInitialized ? appliedGameModes : null // Use applied filters for the query
  );

  const modesKey = appliedGameModes.join("|");

  // Use loading state logic
  const { isInitialLoad } = usePageLoadingState({
    loadingStates: [decksLoading, cardsLoading, gameModesLoading],
    errorStates: [isDecksError, isCardsError, isGameModesError],
    hasData: () =>
      Boolean(
        deckStats?.deck_statistics.decks &&
          deckStats.deck_statistics.decks.length > 0
      ),
    resetDependency: `${playerTag}-${modesKey}`,
  });

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
              <GameModeFilter
                gameModes={gameModes ?? {}}
                selected={selectedGameModes}
                onChange={setSelectedGameModes}
              />
              <button
                type="button"
                className="decks-apply-filters-button"
                onClick={applyAllFilters}
              >
                Apply
              </button>
            </div>
            <h2>Deck Stats</h2>

            {/* Show decks if there is any data to display */}
            {deckStats?.deck_statistics.decks &&
              deckStats.deck_statistics.decks.length > 0 && (
                <>
                  {deckStats.deck_statistics.decks.map((d) => (
                    // Unique deck id of all cards in the deck
                    <div key={`${d.deck?.map((c) => c.id).join(";")}`}>
                      <strong>{d.count}</strong> — {d.wins}
                      <DeckComponent deck={d.deck} cards={cards ?? []} />
                    </div>
                  ))}
                </>
              )}

            {/* Show message when no decks are found and not still loading */}
            {(!deckStats?.deck_statistics.decks ||
              deckStats.deck_statistics.decks.length === 0) &&
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
