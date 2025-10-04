import { formatDateForInput } from "./datetime";
import type { FilterState } from "../components/filter/filter";

/**
 * Saves filter state to localStorage.
 * Serializes the FilterState object to JSON and stores it under the "filterState" key.
 *
 * @param filters - The filter state object to persist
 */
export function setFilterStateToLocalStorage(filters: FilterState) {
  localStorage.setItem("filterState", JSON.stringify(filters));
}

/**
 * Retrieves and parses filter state from localStorage.
 * Attempts to parse the stored JSON data back into a FilterState object.
 *
 * @returns The parsed FilterState object if found and valid, null otherwise
 * @throws Logs an error to console if JSON parsing fails, but returns null instead of throwing
 */
export function getFilterStateFromLocalStorage(): FilterState | null {
  try {
    const filters = localStorage.getItem("filterState");
    if (filters) {
      return JSON.parse(filters);
    }
  } catch (error) {
    console.error("Failed to parse filter state from localStorage:", error);
    return null;
  }
  return null;
}

/**
 * Calculates initial date range for filters.
 * Sets the end date to today and start date to dayOffset (default: 7) days ago.
 *
 * @returns Object containing formatted start and end date strings in YYYY-MM-DD format
 */
export function getDateRange(dayOffset: number = 7) {
  const endDate = new Date();
  const startDate = new Date();
  // Initialize with last dayOffset days as default date range
  startDate.setDate(startDate.getDate() - dayOffset);
  return {
    start: formatDateForInput(startDate),
    end: formatDateForInput(endDate),
  };
}

/**
 * Creates an initial filter state, prioritizing saved state from localStorage with smart date handling.
 * This function is used to persist filter states over different pages and page visits.
 *
 * Behavior:
 * 1. If filters exist in localStorage:
 *    - For non-"Custom" timespan options: Recalculates dates based on the saved timespan
 *    - For "Custom" timespan: Uses the exact saved dates
 *    - Preserves saved game modes and cards
 * 2. If no saved filters: Returns default filter state
 *
 * Default fallback configuration:
 * - Date range: Last 7 days (from today)
 * - Game modes: Empty array (no filters applied)
 * - Cards: Empty array (no filters applied)
 * - Timespan option: "Last 7 days"
 *
 * @returns FilterState object with either restored or default filter values
 */
export function getInitialFilterState(): FilterState {
  const filters = getFilterStateFromLocalStorage();
  // Check if there are filters saved
  if (filters) {
    // If timespan is NOT custom, calculate start and end date new
    if (filters.timespanOption !== "Custom") {
      // Extract which Last X days option is selected
      const daysOption = filters.timespanOption
        .replace("Last ", "")
        .replace(" days", "");
      const days = Number(daysOption);
      const newlyCalcDates = getDateRange(days);

      // Return updated filter state
      return {
        startDate: newlyCalcDates.start,
        endDate: newlyCalcDates.end,
        gameModes: filters.gameModes,
        cards: filters.cards,
        timespanOption: filters.timespanOption,
      };
    }
    // Return (unchanged) saved filter state
    return filters;
  }

  // Return default filter state
  const initialDates = getDateRange(7);
  return {
    startDate: initialDates.start,
    endDate: initialDates.end,
    gameModes: [],
    cards: [],
    timespanOption: "Last 7 days",
  };
}
