import { useParams } from "react-router-dom";
import type { DailyStats, Days } from "../../types/dailyStats";
import { useDailyStats } from "../../hooks/useDailyStats";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { getCurrentFilterState } from "../../utils/filter";
import { useEffect, useState } from "react";
import type { ChartConfig } from "../../types/chart";
import { LineChart } from "../../components/lineChart/lineChart";
import { FilterContainer } from "../../components/filterContainer/filterContainer";
import type { FilterState } from "../../components/filterContainer/filterContainer";
import "./stats.css";

/**
 * Extracts an array of values for a specific field from daily statistics data.
 *
 * This generic function takes daily statistics and extracts all values for a given field
 * across all days, returning them as a typed array. It's particularly useful for creating
 * chart data where you need all values of a specific metric (like battles, winRate, etc.)
 * from multiple days in a single array.
 *
 * @template T - The key type that extends the keys of the Days interface
 * @param stats - The daily statistics data containing an array of daily records, or undefined if not loaded
 * @param key - The specific field name to extract from each daily record (e.g., 'battles', 'winRate', 'date')
 * @returns An array containing all values of the specified field from each day's data.
 *          The return type matches the type of the field (e.g., number[] for 'battles', string[] for 'date')
 *          Returns an empty array if stats is undefined or null.
 *
 * @example
 * // Extract all battle counts across days
 * const battleCounts = getDataArrayForKey(stats, 'battles'); // Returns number[]
 *
 * @example
 * // Extract all dates across days
 * const dates = getDataArrayForKey(stats, 'date'); // Returns string[]
 */
function getDataArrayForKey<T extends keyof Days>(
  stats: DailyStats | undefined,
  key: T
): Days[T][] {
  // Early return with empty array if stats is null/undefined to avoid runtime errors
  if (!stats) return [];

  // Extract the daily array from the nested statistics structure
  const daily = stats.daily_statistics.daily;

  // Initialize typed array to store extracted values - TypeScript infers the correct element type (string or number)
  const data: Days[T][] = [];

  // Iterate through each day's data to extract the specified field value
  for (const day of daily) {
    // Extract the value for the given key and add to results array
    data.push(day[key]);
  }

  // Return the collected values as a typed array ready for chart consumption
  return data;
}

export default function PlayerStats() {
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

  // Card statistics API call
  // Fetch card statistics only when game modes are properly initialized
  // Uses applied filter values (not selected ones) to ensure query stability
  // Passes null for game modes to disable the query until gameModesInitialized is true
  const {
    data: stats,
    isLoading: statsLoading,
    isError: isStatsError,
    error: statsError,
  } = useDailyStats(
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
    loadingStates: [statsLoading, gameModesLoading],
    errorStates: [isStatsError, isGameModesError],
    hasData: () => Boolean(stats && stats.daily_statistics.daily.length > 0),
    // Reset dependency ensures loading state recalculates when any backend filter changes
    resetDependency: `${playerTag}-${appliedFilters.startDate}-${appliedFilters.endDate}-${modesKey}`,
  });

  const winRateChart: ChartConfig = {
    data: getDataArrayForKey(stats, "winRate"),
    labels: getDataArrayForKey(stats, "date"),
    title: "Win Rate %",
    yAxisTitle: "Win Rate %",
    xAxisTitle: "Days",
    chartColor: "#3778daff",
    labelColor: "#c8c2c2e9",
  };

  const battlesChart: ChartConfig = {
    data: getDataArrayForKey(stats, "battles"),
    labels: getDataArrayForKey(stats, "date"),
    title: "Battles",
    yAxisTitle: "Amount of Battles",
    xAxisTitle: "Days",
    chartColor: "#b852e3ff",
    labelColor: "#c8c2c2e9",
  };

  return (
    <div className="stats-page">
      <div className="stats-content">
        {isStatsError && <div>Error: {statsError?.message}</div>}
        {isGameModesError && <div>Error: {gameModesError?.message}</div>}

        {/* Loading State - Shows during initial load, cards loading, card stats loading, or game mode loading */}
        {/* The loading spinner prevents users from seeing incomplete data during the initialization process */}
        {(isInitialLoad || statsLoading || gameModesLoading) && (
          <div>
            <CircularProgress className="stats-loading-spinner" />
            <p>Loading statistics...</p>
          </div>
        )}
        {/* Loaded State - Show decks when all data is available and no errors occurred */}
        {!isGameModesError && !isInitialLoad && (
          <>
            {/* FilterContainer component */}
            <FilterContainer
              gameModes={gameModes || {}}
              cards={[]}
              gameModesLoading={gameModesLoading}
              onFiltersApply={handleFiltersApply}
              showCardFilter={false}
              appliedFilters={appliedFilters}
              initialFilters={getCurrentFilterState()}
            />

            {/* Show stats if there is any data to display */}
            {stats && stats.daily_statistics.daily.length > 0 && (
              <div className="stats-charts">
                <LineChart config={winRateChart} />
                <LineChart config={battlesChart} />
              </div>
            )}

            {/* Show message when no cards are found and not still loading */}
            {(!stats || stats.daily_statistics.daily.length === 0) &&
              !statsLoading &&
              !gameModesLoading &&
              !statsLoading && (
                <div className="no-stats-message">
                  <p>No statistics found with the current filters applied</p>
                </div>
              )}
          </>
        )}
      </div>
    </div>
  );
}
