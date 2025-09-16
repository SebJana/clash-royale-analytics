import { useParams } from "react-router-dom";
import { useEffect, useMemo, useState, useCallback } from "react";
import { useCards } from "../../hooks/useCards";
import { usePlayerBattlesInfinite } from "../../hooks/useLastBattles";
import { BattleComponent } from "../../components/battle/battle";
import { localeToUTC, getTodayDateTime } from "../../utils/datetime";
import "./battles.css";

export default function PlayerBattles() {
  const { playerTag = "" } = useParams();

  const [beforeDate, setBeforeDate] = useState(getTodayDateTime()); // Pre-fill with today's date and time (string and locale time)
  const [appliedBeforeDate, setAppliedBeforeDate] = useState<
    string | undefined
  >(undefined); // Store the applied filter date in UTC
  const [isValidFilterDate, setIsValidFilterDate] = useState(true); // Initially true since we start with today's date

  const {
    data: cards,
    isLoading: cardsLoading,
    isError: isCardsError,
    error: cardsError,
  } = useCards();

  const {
    data: battles,
    isLoading: battlesLoading,
    isError: isBattlesError,
    error: battlesError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = usePlayerBattlesInfinite(playerTag, 3, true, appliedBeforeDate);

  const battlesList = useMemo(
    () => battles?.pages.flatMap((p) => p.last_battles.battles) ?? [],
    [battles]
  );

  // Check if there is a valid date that is not in the future
  const validateFilterDate = useCallback((dateString: string): boolean => {
    if (!dateString) {
      return false;
    }

    const selectedDate = new Date(dateString);

    // Check if the date is valid
    return !isNaN(selectedDate.getTime());
  }, []);

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

  const handleClearFilter = () => {
    setAppliedBeforeDate(undefined);
    setBeforeDate(getTodayDateTime());
  };

  // Check if the date in the filter is valid (enabling 'Apply Filter' button)
  useEffect(() => {
    const isValid = validateFilterDate(beforeDate);
    setIsValidFilterDate(isValid);
  }, [beforeDate, validateFilterDate]);

  // Handle cards error early
  if (isCardsError) return <div>Error: {cardsError.message}</div>;

  return (
    <div className="battles-page">
      <div className="battles-filter-container">
        <label className="battles-datetime-label" htmlFor="beforeDate">
          See battles before:
        </label>
        <input
          className="battles-datetime-input"
          type="datetime-local"
          name="beforeDate"
          id="beforeDate"
          value={beforeDate}
          onChange={(e) => setBeforeDate(e.target.value)}
          style={{
            // Signal invalid date
            borderColor: !isValidFilterDate ? "#ff6b6b" : undefined,
          }}
        />
        <button
          className="battles-apply-filter-button"
          disabled={!isValidFilterDate}
          onClick={handleApplyFilter}
        >
          Apply Filter
        </button>
        <button
          className="battles-clear-filter-button"
          onClick={handleClearFilter}
        >
          Clear Filter
        </button>
      </div>

      {/* Battles content with stable height */}
      <div className="battles-content">
        {isBattlesError && <div>Error: {battlesError.message}</div>}

        {(battlesLoading || cardsLoading) && <div>Loading battles...</div>}

        {!isBattlesError && !battlesLoading && !cardsLoading && (
          <>
            {battlesList.map((b, i) => (
              <BattleComponent
                key={`${b.battleTime}-${playerTag}-${i}`} // More stable unique ID
                battle={b}
                cards={cards ?? []} // fall back to empty list, if cards don't exist
              />
            ))}

            {hasNextPage ? (
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? "Loading..." : "Load more"}
              </button>
            ) : (
              // TODO upon reloading with many loaded battles, user sees "No more battles", but should see loading spinner
              <div>No more battles</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
