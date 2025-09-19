import { useCards } from "../../hooks/useCards";
import { useParams } from "react-router-dom";
import { useDeckStats } from "../../hooks/useDeckStats";
import { DeckComponent } from "../../components/deck/deck";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";

export default function PlayerDecks() {
  const { playerTag = "" } = useParams();

  const {
    data: cards,
    isLoading: cardsLoading,
    isError: isCardsError,
    error: cardsError,
  } = useCards();

  // Fetch decks statistics
  const {
    data: deckStats,
    isLoading: decksLoading,
    isError: isDecksError,
    error: decksError,
  } = useDeckStats(playerTag, "2025-01-01", "2025-10-01");

  // Use loading state logic
  const { isInitialLoad } = usePageLoadingState({
    loadingStates: [decksLoading, cardsLoading],
    errorStates: [isDecksError, isCardsError],
    hasData: () =>
      Boolean(
        deckStats?.deck_statistics.decks &&
          deckStats.deck_statistics.decks.length > 0
      ),
    resetDependency: playerTag,
  });

  return (
    <div className="decks-page">
      <div className="decks-content">
        {isDecksError && <div>Error: {decksError?.message}</div>}
        {isCardsError && <div>Error: {cardsError?.message}</div>}

        {/* Loading State - Shows during initial load, cards loading, or decks loading */}
        {/* By showing a loading spinner, the user can access the site instantly and doesn't have
            to wait on the previous site till all decks loaded and rendered */}
        {(isInitialLoad || decksLoading || cardsLoading) && (
          <div>
            <CircularProgress className="decks-loading-spinner" />
            <p>Loading decks...</p>
          </div>
        )}
        {/* Loaded State - Show decks when all data is available and no errors occurred */}
        {!isDecksError && !isInitialLoad && (
          <>
            <h2>Deck Stats</h2>

            {/* Show decks if there is any data to display */}
            {deckStats?.deck_statistics.decks &&
              deckStats.deck_statistics.decks.length > 0 && (
                <>
                  {deckStats.deck_statistics.decks.map((d) => (
                    // Unique deck id of all cards in the deck
                    <div key={d.deck?.map((c) => c.id).join(";")}>
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
