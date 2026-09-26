import { useCards } from "../../hooks/useCards";
import { useParams } from "react-router-dom";
import { useDeckStats } from "../../hooks/useDeckStats";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import { DeckComponent } from "../../components/deck/deck";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { round } from "../../utils/number";
import { pluralize } from "../../utils/plural";
import { getCurrentFilterState } from "../../utils/filter";
import { gameModesForQuery } from "../../utils/gameModes";
import { datetimeToLocale } from "../../utils/datetime";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import type { RefObject } from "react";
import { StatCard } from "../../components/statCard/statCard";
import { ScrollToTopButton } from "../../components/scrollToTop/scrollToTop";
import { FilterContainer } from "../../components/filterContainer/filterContainer";
import type { FilterState } from "../../components/filterContainer/filterContainer";
import { SortByContainer } from "../../components/sortByContainer/sortByContainer";
import type { Card, CardMeta } from "../../types/cards";
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
  totalBattles: number,
) {
  const usageRate = (battleCount / totalBattles) * 100; // In percent
  const roundedUsageRate = round(usageRate, 1);
  return `${roundedUsageRate}%`;
}

function VirtualDeckList({
  decks,
  cards,
  totalBattles,
  showMatch,
  matchedCards,
  scrollingToTopRef,
}: Readonly<{
  decks: (Deck | DeckWithMatchScore)[];
  cards: CardMeta[];
  totalBattles: number;
  showMatch: boolean;
  matchedCards: Card[];
  scrollingToTopRef: RefObject<boolean>;
}>) {
  const listRef = useRef<HTMLDivElement>(null);
  const [scrollMargin, setScrollMargin] = useState(0);

  // Only render deck rows near the visible part of the page.
  // Row heights are measured after rendering because they vary with screen width.
  const virtualizer = useWindowVirtualizer({
    count: decks.length, // Total number of decks the user can scroll through
    estimateSize: () => 420, // Initial row height in pixels, before its actual height is measured
    overscan: 3, // Render three extra rows above and below the visible area
    scrollMargin, // Distance from the top of the page to the start of the deck list
  });

  // Filtering can reuse a mounted row for a different deck. Measure it again
  // immediately so a stale row height does not shift decks into each other.
  // Scrolling a row out and back in does the same measurement on remount.
  const measureRow = useCallback(
    (element: HTMLDivElement | null) => {
      if (element && !decks[Number(element.dataset.index)]) return;
      virtualizer.measureElement(element);
    },
    [decks, virtualizer],
  );

  useLayoutEffect(() => {
    // Measuring rows above the viewport can interrupt the Back to Top animation.
    virtualizer.shouldAdjustScrollPositionOnItemSizeChange = (
      item,
      _delta,
      instance,
    ) =>
      !scrollingToTopRef.current && item.start < (instance.scrollOffset ?? 0);
    return () => {
      virtualizer.shouldAdjustScrollPositionOnItemSizeChange = undefined;
    };
  }, [virtualizer, scrollingToTopRef]);

  useLayoutEffect(() => {
    const updateScrollMargin = () => {
      if (listRef.current) {
        setScrollMargin(
          listRef.current.getBoundingClientRect().top + window.scrollY,
        );
      }
    };
    updateScrollMargin();
    // Expanding the filters moves the list without resizing the window.
    const resizeObserver = new ResizeObserver(updateScrollMargin);
    const content = listRef.current?.closest(".decks-content");
    if (content) {
      resizeObserver.observe(content);
      content
        .querySelectorAll(
          ".filter-component-container, .sort-by-container, .decks-general-stats",
        )
        .forEach((element) => resizeObserver.observe(element));
    }
    window.addEventListener("resize", updateScrollMargin);
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateScrollMargin);
    };
  }, []);

  return (
    // Keep the full scroll height even though only nearby rows are rendered.
    <div
      ref={listRef}
      className="decks-virtual-list"
      style={{ height: virtualizer.getTotalSize() }}
    >
      {virtualizer.getVirtualItems().map((virtualRow) => {
        const d = decks[virtualRow.index];
        return (
          <div
            key={virtualRow.key}
            data-index={virtualRow.index}
            ref={measureRow}
            className="decks-deck-row"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              // virtualRow.start includes the list's page offset; CSS uses list coordinates.
              transform: `translateY(${virtualRow.start - scrollMargin}px)`,
            }}
          >
            <div className="deck-section">
              {showMatch && "matchPercentage" in d && (
                <div className="decks-card-match-header">
                  <span className="decks-card-match-value">{`${round(
                    d.matchPercentage,
                    1,
                  )}% (${d.matchCount} matching ${pluralize(
                    d.matchCount,
                    "Card",
                    "Cards",
                  )})`}</span>
                  <span className="decks-card-match-label">Card Match</span>
                </div>
              )}
              <DeckComponent
                deck={d.deck}
                cards={cards}
                matchedCards={showMatch ? matchedCards : undefined}
              />
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
              <StatCard label="Win Rate" value={`${round(d.winRate, 1)}%`} />
              <StatCard
                label="Usage Rate"
                value={calculateAndFormatUsageRate(d.count, totalBattles)}
              />
              <StatCard
                label={pluralize(d.modes.length, "Game Mode", "Game Modes")}
                value={d.modes.length}
              />
              <StatCard
                label="Last Seen"
                value={datetimeToLocale(d.lastSeen)}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// TODO add same error handling for all pages if no data is found or the tag is invalid
export default function PlayerDecks() {
  const { playerTag = "" } = useParams();
  const scrollingToTopRef = useRef(false);
  const scrollResetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  useEffect(() => {
    const resetAtTop = () => {
      if (window.scrollY <= 1) scrollingToTopRef.current = false;
    };
    const cancelScrollToTop = () => {
      scrollingToTopRef.current = false;
    };
    window.addEventListener("scroll", resetAtTop);
    window.addEventListener("wheel", cancelScrollToTop);
    window.addEventListener("touchstart", cancelScrollToTop);
    window.addEventListener("keydown", cancelScrollToTop);
    return () => {
      window.removeEventListener("scroll", resetAtTop);
      window.removeEventListener("wheel", cancelScrollToTop);
      window.removeEventListener("touchstart", cancelScrollToTop);
      window.removeEventListener("keydown", cancelScrollToTop);
      if (scrollResetTimeoutRef.current)
        clearTimeout(scrollResetTimeoutRef.current);
    };
  }, []);

  const handleScrollToTopStart = () => {
    scrollingToTopRef.current = true;
    if (scrollResetTimeoutRef.current)
      clearTimeout(scrollResetTimeoutRef.current);
    // Also restore normal scroll adjustments if the user interrupts the animation.
    scrollResetTimeoutRef.current = setTimeout(() => {
      scrollingToTopRef.current = false;
    }, 3000);
  };

  // Filter state management maintains two sets of state for each filter type:
  // 1. "selected" - what the user has chosen in the UI (not yet applied)
  // 2. "applied" - what is actually used for the API query (in case of cards for the frontend filter)
  // This allows users to configure multiple filters before applying them all at once to reduce API calls and loading times

  // State to store applied filters from FilterContainer
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(
    getCurrentFilterState(),
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
  // An empty selection means all modes and deliberately omits game_modes from
  // the request. Do not expand it to the current list of mode keys: a new mode
  // can exist in battle data before it appears in the cached mode list.
  useEffect(() => {
    if (gameModes && !gameModesInitialized && !gameModesLoading) {
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
  const queryGameModes = gameModesInitialized
    ? gameModesForQuery(appliedFilters.gameModes, gameModes)
    : null;
  const {
    data: deckStats,
    isLoading: decksLoading,
    isError: isDecksError,
    error: decksError,
  } = useDeckStats(
    playerTag,
    appliedFilters.startDate,
    appliedFilters.endDate,
    queryGameModes,
  );

  // Helper function to check if a deck contains a specific card
  const deckContainsCard = (deck: Deck, appliedCard: Card) => {
    return deck.deck?.some(
      (deckCard) =>
        deckCard.id === appliedCard.id &&
        (deckCard.evolutionLevel ?? 0) === (appliedCard.evolutionLevel ?? 0),
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
      deckContainsCard(deck, appliedCard),
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
        // Usage rate has the same ordering as battle count because every deck
        // uses the same total number of battles as its denominator.
        valueA = a.count;
        valueB = b.count;
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
          deckContainsCard(deck, appliedCard),
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

  // Use the modes actually sent to the API for the loading state dependency.
  const modesKey = queryGameModes?.join("|") ?? "";

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
                <VirtualDeckList
                  decks={filteredDecks}
                  cards={cards ?? []}
                  totalBattles={totalBattles}
                  matchedCards={appliedFilters.cards}
                  scrollingToTopRef={scrollingToTopRef}
                  showMatch={
                    !appliedFilters.includeCardFilterMode &&
                    appliedFilters.cards.length > 0
                  }
                />
              </div>
            )}
            <ScrollToTopButton onScrollStart={handleScrollToTopStart} />

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
