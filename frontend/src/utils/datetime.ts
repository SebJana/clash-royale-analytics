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
