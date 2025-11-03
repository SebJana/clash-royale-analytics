/**
 * Format an API timestamp in the user's locale.
 * Assumes UTC if no timezone is present; returns "—" if invalid.
 * @param time ISO 8601 string (e.g. "2025-09-08T22:52:42")
 * @returns Localized date-time string
 */
export function datetimeToLocale(time: string): string {
  if (!time) return "—";

  // Does the datetime string already have an ending 'Z' for UTC time?
  const hasTZ = /(Z|[+-]\d{2}:\d{2})$/i.test(time);
  let iso: string;
  if (hasTZ) {
    iso = time;
  } else {
    // Append if not yet there
    iso = time + "Z";
  }

  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";

  // Locale & timezone of user
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(d);
}

/**
 * Convert a local time string to UTC ISO format.
 * @param time Local time string
 * @returns UTC ISO string (e.g., "2025-09-16T14:30:00.000Z")
 */
export function localeToUTC(time: string): string {
  const localDate = new Date(time); // interpret as local time
  return localDate.toISOString(); // convert to UTC ISO string
}

/**
 * Get the current date and time in the format required for datetime-local input.
 * @returns Current date-time in YYYY-MM-DDTHH:MM format
 */
export function getTodayDateTime(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Helper function to format date for input fields
 * @param date date-time in YYYY-MM-DDTHH:MM format
 * @returns YYYY-MM-DD format
 */
export function formatDateForInput(date: Date): string {
  return date.toISOString().slice(0, 10); // Format as YYYY-MM-DD
}

/**
 * Returns the release date of Clash Royale.
 *
 * @returns A `Date` object representing March 2, 2016.
 */
export function getClashRoyaleReleaseDate(): Date {
  // Official launch date for Clash Royale
  return new Date("2016-03-02");
}

/**
 * Validates that a date range is valid within the allowed boundaries.
 *
 * @param startDateString - The start date string in a YYYY-MM-DD format.
 * @param endDateString - The end date string in a YYYY-MM-DD format.
 * @returns `true` if:
 * - Both strings represent valid dates
 * - The start date is not before the Clash Royale release date
 * - The end date is not in the future
 * - The end date is the same or after the start date
 *
 * Otherwise returns `false`.
 */
export function isValidDateRange(
  startDateString: string,
  endDateString: string
) {
  if (!startDateString || !endDateString) {
    return false;
  }

  // Convert to dates
  const startDate = new Date(startDateString);
  const endDate = new Date(endDateString);

  // When the given strings can't be converted into a valid date
  if (
    !startDate ||
    Number.isNaN(startDate.getTime()) ||
    !endDate ||
    Number.isNaN(endDate.getTime())
  ) {
    return false;
  }

  const today = new Date();

  // Upon selecting an end date in the future
  if (endDate > today) {
    return false;
  }
  // Upon selecting a start date too far in the past (before the Clash Royale launch)
  if (startDate < getClashRoyaleReleaseDate()) {
    return false;
  }

  // End date is before start date
  if (endDate < startDate) {
    return false;
  }
  // TODO possibly limit time range (max N years)?
  return true;
}
