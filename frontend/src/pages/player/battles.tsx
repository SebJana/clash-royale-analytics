import { useParams } from "react-router-dom";
import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { useCards } from "../../hooks/useCards";
import { usePlayerBattlesInfinite } from "../../hooks/useLastBattles";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import { BattleComponent } from "../../components/battle/battle";
import { ScrollToTopButton } from "../../components/scrollToTop/scrollToTop";
import { localeToUTC, getTodayDateTime } from "../../utils/datetime";
import CircularProgress from "@mui/material/CircularProgress";
import "./battles.css";

/**
 * PlayerBattles Component
 *
 * Displays a paginated list of battles for a specific player with the following features:
 * - Date/time filtering to show battles before a specific date
 * - Infinite scroll pagination for loading more battles
 * - Loading states for better UX
 * - Error handling for failed API calls
 */
export default function PlayerBattles() {
  // Extract player tag from URL parameters
  const { playerTag = "" } = useParams();

  // Filter state: date input field value (in local timezone)
  const [beforeDate, setBeforeDate] = useState(getTodayDateTime()); // Pre-fill with today's date and time

  // Applied filter state: the actual filter being used for API calls (in UTC)
  const [appliedBeforeDate, setAppliedBeforeDate] = useState<
    string | undefined
  >(undefined);

  // Validation state: tracks if the current date input is valid
  const [isValidFilterDate, setIsValidFilterDate] = useState(true); // Initially true since filter starts with today's date

  // Apply button state: tracks if the apply button should be disabled
  const [applyButtonDisabled, setApplyButtonDisabled] = useState(true); // Initially true since no filter is applied

  // Ref for the load more trigger element (used for intersection observer)
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Amount of battles that can be loaded at once from a certain filter datetime
  // NOTE: adjust this to handle load on server for users that scroll indefinitely instead of filtering (also effects rendering time)
  const maxLoadedBattles = 100;
  // State signaling that cap is reached
  const [loadingCapReached, setLoadingCapReached] = useState(false);

  // Fetch card data (needed to display card information in battles)
  const {
    data: cards,
    isLoading: cardsLoading,
    isError: isCardsError,
    error: cardsError,
  } = useCards();

  // Fetch battles with infinite pagination
  const {
    data: battles,
    isLoading: battlesLoading,
    isError: isBattlesError,
    error: battlesError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = usePlayerBattlesInfinite(playerTag, 3, true, appliedBeforeDate); // Reduced page size (3) for better UX | loading/rendering times

  // Flatten paginated battle data into a single array for easier rendering
  const battlesList = useMemo(
    () => battles?.pages.flatMap((p) => p.last_battles.battles) ?? [],
    [battles]
  );

  // Use loading state logic
  const { isInitialLoad } = usePageLoadingState({
    loadingStates: [battlesLoading, cardsLoading],
    errorStates: [isBattlesError, isCardsError],
    hasData: () => battlesList.length > 0,
    resetDependency: `${playerTag}-${appliedBeforeDate}`,
  });

  // Intersection Observer for auto-loading more battles when user scrolls near bottom
  useEffect(() => {
    const loadMoreElement = loadMoreRef.current;
    if (
      loadingCapReached ||
      !loadMoreElement ||
      !hasNextPage ||
      isFetchingNextPage
    )
      return;

    // Set up intersection observer to trigger loading when element becomes visible
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        // Only fetch more if the trigger element is visible and we can load more
        // Also ensure we're not in initial load state to avoid conflicts
        if (
          entry.isIntersecting &&
          hasNextPage &&
          !isFetchingNextPage &&
          !isInitialLoad
        ) {
          fetchNextPage();
        }
      },
      {
        rootMargin: "500px", // Start loading before the element comes into view
        threshold: 0.1, // Trigger when 10% of the element is visible
      }
    );

    observer.observe(loadMoreElement);

    // Cleanup function to disconnect observer
    return () => {
      observer.disconnect();
    };
  }, [
    fetchNextPage,
    loadingCapReached,
    hasNextPage,
    isFetchingNextPage,
    isInitialLoad,
  ]);

  /**
   * Validates if a date string represents a valid date
   * @param dateString - The date string to validate
   * @returns true if the date is valid, false otherwise
   */
  const validateFilterDate = useCallback((dateString: string): boolean => {
    // When there is no given date
    if (!dateString) {
      return false;
    }

    const selectedDate = new Date(dateString);
    // When the given string can't be converted into a valid date
    if (!selectedDate || Number.isNaN(selectedDate.getTime())) {
      return false;
    }

    // Set the max date to today + 1 (tomorrow at 00:00)
    // Enables a little buffer space for users setting the filter date ever so slightly into the future
    const maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 1);
    maxDate.setHours(0, 0, 0, 0);

    // Official launch date for Clash Royale
    // Tracked Battles are will (most likely) not exist that far back, but set that as fixed range start
    const clashRoyaleLaunchDate = new Date("2016-03-02T00:00:00Z");

    // Upon inserting a date in the future
    if (selectedDate > maxDate) {
      return false;
    }
    // Upon selecting a date too far in the past (before the Clash Royale launch)
    if (selectedDate < clashRoyaleLaunchDate) {
      return false;
    }

    return true;
  }, []);

  // Keep track of how many battles are currently loaded and set the flag
  // Reset/Clear the flag if there are less
  useEffect(() => {
    const amountOfBattles = battlesList.length;
    if (amountOfBattles >= maxLoadedBattles) {
      setLoadingCapReached(true);
    }
    // Reset the flag if there are now less battles --> loaded page/filter/player changed
    else if (loadingCapReached) {
      setLoadingCapReached(false);
    }
  }, [battlesList, loadingCapReached, setLoadingCapReached]);

  // Validate date input and update filter validity state
  useEffect(() => {
    const isValid = validateFilterDate(beforeDate);
    setIsValidFilterDate(isValid);
  }, [beforeDate, validateFilterDate]);

  // Apply button logic - enable only when date has changed and is valid
  useEffect(() => {
    // Check if the current selected date (converted to UTC) differs from applied date
    const currentSelectedDateUTC =
      beforeDate && isValidFilterDate ? localeToUTC(beforeDate) : undefined;

    // If date is invalid it will differ from the applied date, but the button will be disabled via 'isValidFilterDate'
    if (currentSelectedDateUTC === appliedBeforeDate) {
      setApplyButtonDisabled(true); // Disable button when no change
    } else {
      setApplyButtonDisabled(false); // Enable button when there's a change
    }
  }, [beforeDate, appliedBeforeDate, isValidFilterDate]);

  /**
   * Applies the current date filter to the battles query
   * Converts local time to UTC before applying the filter
   */
  const handleApplyFilter = () => {
    if (beforeDate && isValidFilterDate) {
      // Convert local datetime to UTC for API
      const utcDate = localeToUTC(beforeDate);
      setAppliedBeforeDate(utcDate);
    } else {
      // Clear filter if no date is selected
      setAppliedBeforeDate(undefined);
    }
  };

  /**
   * Clears the applied filter and resets the date input to today
   */
  const handleResetFilter = () => {
    setAppliedBeforeDate(undefined);
    setBeforeDate(getTodayDateTime());
  };

  // Handle cards error early - battles can't be displayed without card data
  if (isCardsError) return <div>Error: {cardsError.message}</div>;

  return (
    <div className="battles-page">
      {/* Filter Controls Section */}
      <div className="battles-filter-container">
        <label className="battles-datetime-label" htmlFor="beforeDate">
          See battles before:
        </label>
        <input
          className={`battles-datetime-input${
            isValidFilterDate ? "" : " invalid"
          }`}
          type="datetime-local"
          name="beforeDate"
          id="beforeDate"
          value={beforeDate}
          onChange={(e) => setBeforeDate(e.target.value)}
        />
        <button
          className="battles-apply-filter-button"
          disabled={!isValidFilterDate || applyButtonDisabled}
          onClick={handleApplyFilter}
        >
          Apply
        </button>
        <button
          className="battles-clear-filter-button"
          onClick={handleResetFilter}
        >
          Reset
        </button>
      </div>

      <div className="battles-content">
        {isBattlesError && <div>Error: {battlesError.message}</div>}

        {/* Loading State - Shows during initial load, cards loading, or battles loading */}
        {/* By showing a loading spinner, the user can access the site instantly and doesn't have
            to wait on the previous site till all battles loaded and rendered */}
        {(isInitialLoad || battlesLoading || cardsLoading) && (
          <div>
            <CircularProgress className="battles-loading-spinner" />
            <p>Loading battles...</p>
          </div>
        )}

        {/* Loaded State - Show battles when all data is available and no errors occurred */}
        {!isBattlesError && !isInitialLoad && (
          <>
            {/* Show battles if there is any data to display */}
            {battlesList.length > 0 && (
              <>
                {battlesList.map((b, i) => (
                  <BattleComponent
                    key={`${b.battleTime}-${playerTag}-${i}`} // More stable unique ID
                    battle={b}
                    cards={cards ?? []} // fall back to empty list, if cards don't exist
                  />
                ))}

                {/* Infinite Scroll Trigger - Hidden element that triggers loading when visible */}
                {hasNextPage && (
                  <div ref={loadMoreRef} className="battles-load-more-trigger">
                    {isFetchingNextPage && (
                      <div className="battles-loading-more">
                        <CircularProgress className="battles-loading-spinner" />
                        <span>Loading more battles...</span>
                      </div>
                    )}
                  </div>
                )}

                {/* End of List Message - Show when all battles have been loaded */}
                {!hasNextPage && (
                  <div className="battles-end-user-message">
                    <p>No more battles to load</p>
                  </div>
                )}
              </>
            )}
            <ScrollToTopButton />

            {/* Show message when loading cap is reached */}
            {battlesList.length !== 0 && loadingCapReached && (
              <div className="battles-end-user-message">
                <p>
                  You’ve reached the maximum number of battles shown. Adjust the
                  filter to view earlier ones.
                </p>
              </div>
            )}

            {/* Show message when no battles are found and not loading */}
            {battlesList.length === 0 && !battlesLoading && !cardsLoading && (
              <div className="battles-end-user-message">
                <p>No battles found</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
