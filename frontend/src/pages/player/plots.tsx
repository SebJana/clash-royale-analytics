import { useParams } from "react-router-dom";
import type { DailyStats, Days } from "../../types/dailyStats";
import { useDailyStats } from "../../hooks/useDailyStats";
import { usePageLoadingState } from "../../hooks/usePageLoadingState";
import CircularProgress from "@mui/material/CircularProgress";
import { useGameModes } from "../../hooks/useGameModes";
import { getCurrentFilterState } from "../../utils/filter";
import { gameModesForQuery } from "../../utils/gameModes";
import { useEffect, useState } from "react";
import { ScrollToTopButton } from "../../components/scrollToTop/scrollToTop";
import type { ChartConfig } from "../../types/chart";
import { LineChart } from "../../components/lineChart/lineChart";
import { FilterContainer } from "../../components/filterContainer/filterContainer";
import type { FilterState } from "../../components/filterContainer/filterContainer";
import "./plots.css";

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
  key: T,
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

/**
 * Calculates the average leaked elixir per battle for each day in the statistics data.
 *
 * @param stats - The daily statistics data containing an array of daily records, or undefined if not loaded
 * @returns An array of numbers representing the average leaked elixir per battle for each given day.
 *          Each element corresponds to one day's average leaked elixir efficiency.
 *          Returns an empty array if stats is undefined or null.
 *          If a day has 0 battles, returns the total leaked elixir value (not divided by zero).

 */
function getLeakedElixirPerMatch(stats: DailyStats | undefined): number[] {
  if (!stats) return [];

  const averageLeaked: number[] = [];

  const daily = stats.daily_statistics.daily;

  for (const day of daily) {
    const battles = day.battles;
    const leakedElixir = day.elixirLeaked;

    let averageLeakedElixir = leakedElixir;

    // Calculate average only if battles were played to avoid division by zero
    // Should not happen, that there is an entry without a played battle, but fallback value is leakedElixir
    if (battles > 0) {
      averageLeakedElixir = leakedElixir / battles;
    }

    // Add the calculated average to the results array
    averageLeaked.push(averageLeakedElixir);
  }

  return averageLeaked;
}

export default function PlayerPlots() {
  const { playerTag = "" } = useParams();

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

  // Card statistics API call
  // Fetch card statistics only when game modes are properly initialized
  // Uses applied filter values (not selected ones) to ensure query stability
  // Passes null for game modes to disable the query until gameModesInitialized is true
  const queryGameModes = gameModesInitialized
    ? gameModesForQuery(appliedFilters.gameModes, gameModes)
    : null;
  const {
    data: stats,
    isLoading: statsLoading,
    isError: isStatsError,
    error: statsError,
  } = useDailyStats(
    playerTag,
    appliedFilters.startDate,
    appliedFilters.endDate,
    queryGameModes,
  );

  // Use the modes actually sent to the API for the loading state dependency.
  const modesKey = queryGameModes?.join("|") ?? "";

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
    datasets: [
      {
        data: getDataArrayForKey(stats, "winRate"),
        label: "Win Rate",
        color: "#00C9FF",
      },
    ],
    labels: getDataArrayForKey(stats, "date"),
    title: "🏆 Win Rate Performance",
    yAxisTitle: "Win Rate (%)",
    xAxisTitle: "Date",
    labelColor: "#e0e0e0",
  };

  const battlesChart: ChartConfig = {
    datasets: [
      {
        data: getDataArrayForKey(stats, "battles"),
        label: "Battles",
        color: "#FF6B6B",
      },
    ],
    labels: getDataArrayForKey(stats, "date"),
    title: "⚔️ Battle Activity",
    yAxisTitle: "Number of Battles",
    xAxisTitle: "Date",
    labelColor: "#e0e0e0",
  };

  const leakedElixirChart: ChartConfig = {
    datasets: [
      {
        data: getLeakedElixirPerMatch(stats),
        label: "Leaked Elixir",
        color: "#C547DB",
      },
    ],
    labels: getDataArrayForKey(stats, "date"),
    title: "🩸 Average Leaked Elixir per Battle",
    yAxisTitle: "Leaked Elixir",
    xAxisTitle: "Date",
    labelColor: "#e0e0e0",
  };

  const crownsChart: ChartConfig = {
    datasets: [
      {
        data: getDataArrayForKey(stats, "crownsFor"),
        label: "Crowns For",
        color: "#00C9FF",
      },
      {
        data: getDataArrayForKey(stats, "crownsAgainst"),
        label: "Crowns Against",
        color: "#FF6B6B",
      },
    ],
    labels: getDataArrayForKey(stats, "date"),
    title: "👑 Crowns For vs. Crowns Against",
    yAxisTitle: "Crowns",
    xAxisTitle: "Date",
    labelColor: "#e0e0e0",
    showLegend: true,
  };

  return (
    <div className="plots-page">
      <div className="plots-content">
        {isStatsError && <div>Error: {statsError?.message}</div>}
        {isGameModesError && <div>Error: {gameModesError?.message}</div>}

        {/* Loading State - Shows during initial load, cards loading, card stats loading, or game mode loading */}
        {/* The loading spinner prevents users from seeing incomplete data during the initialization process */}
        {(isInitialLoad || statsLoading || gameModesLoading) && (
          <div>
            <CircularProgress className="plots-loading-spinner" />
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
              <div className="plots-charts">
                <LineChart className="stat-chart" config={winRateChart} />
                <LineChart className="stat-chart" config={battlesChart} />
                <LineChart className="stat-chart" config={crownsChart} />
                <LineChart className="stat-chart" config={leakedElixirChart} />
              </div>
            )}
            <ScrollToTopButton />

            {/* Show message when no stats are found and not still loading */}
            {(!stats || stats.daily_statistics.daily.length === 0) &&
              !statsLoading &&
              !gameModesLoading &&
              !statsLoading && (
                <div className="no-plots-message">
                  <p>No statistics found with the current filters applied</p>
                </div>
              )}
          </>
        )}
      </div>
    </div>
  );
}
