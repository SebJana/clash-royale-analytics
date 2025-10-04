import { formatDateForInput } from "./datetime";
import type { FilterState } from "../components/filter/filter";

/**
 * Calculates initial date range for filters.
 * Sets the end date to today and start date to 7 days ago.
 *
 * @returns Object containing formatted start and end date strings in YYYY-MM-DD format
 */
export function getInitialDates() {
  const endDate = new Date();
  const startDate = new Date();
  // Initialize with last 7 days as default date range
  // This provides a slim default range that shows recent deck data immediately
  // NOTE: when change is made to this span here, also adjust the initial timespanOption
  // in getInitialFilterState()
  startDate.setDate(startDate.getDate() - 7);
  return {
    start: formatDateForInput(startDate),
    end: formatDateForInput(endDate),
  };
}

/**
 * Creates an initial filter state with default values.
 *
 * Default configuration:
 * - Date range: Last 7 days (from today)
 * - Game modes: Empty array (no filters applied)
 * - Cards: Empty array (no filters applied)
 * - Timespan option: "Last 7 days"
 *
 * @returns FilterState object with default filter values
 */
export function getInitialFilterState(): FilterState {
  const initialDates = getInitialDates();

  return {
    startDate: initialDates.start,
    endDate: initialDates.end,
    gameModes: [],
    cards: [],
    timespanOption: "Last 7 days",
  };
}
