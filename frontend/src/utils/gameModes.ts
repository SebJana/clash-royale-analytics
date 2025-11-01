/**
 * Builds a mapping from internal game mode names (as provided by the API/DB)
 * to user-friendly display names.
 *
 * @param gameModes - A record of internal game mode names as keys, with any lastSeen timestamp as value
 * @returns A Map where the key is the internal name and the value is the display name.
 *
 * @example
 * const gameModes = {
 *   Ranked1v1_NewArena: "2025-09-19T18:32:12.746000",
 *   CaptureTheEgg_Friendly: "2025-09-19T18:32:12.746000"
 * };
 *
 */
export function internalNamesToDisplayNames(
  gameModes: Record<string, string>
): Map<string, string> {
  const internalAndDisplayNames = new Map<string, string>();

  for (const internalName of Object.keys(gameModes)) {
    const displayName = mapInternalNameToDisplayName(internalName);
    // e.g ("Ranked1v1_NewArena", "Ranked 1v1")
    // e.g ("Ranked1v1_NewArena2", "Ranked 1v1")
    internalAndDisplayNames.set(internalName, displayName);
  }

  return internalAndDisplayNames;
}

/**
 * Maps an internal game mode name into a user-friendly display name.
 *
 * Handles special cases like Ranked, Clan Wars, and Friendly modes ...
 * and falls back to a generic transformation (underscores → spaces,
 * split camel case, collapse spaces, and trim) for non-mapped game modes.
 *
 * @param internalName - The raw internal game mode name from the API/DB.
 * @returns A cleaned, human-friendly display name string.
 *
 * @example
 * mapInternalNameToDisplayName("Ranked1v1_NewArena");
 * // "Ranked 1v1"
 */
export function mapInternalNameToDisplayName(internalName: string): string {
  if (internalName.startsWith("Ranked1v1_")) {
    return "Ranked 1v1";
  }
  if (internalName.startsWith("CW_")) {
    return "Clan Wars";
  }
  if (internalName.startsWith("ClanWar_BoatBattle")) {
    return "Clan Wars Boat Battle";
  }
  if (internalName.includes("Friendly")) {
    return "Friendly";
  }
  if (internalName.startsWith("Challenge_AllCards_EventDeck_NoSet")) {
    return "CRL 20-Win";
  }
  // Add new mappings here

  // Fallback: underscores to spaces, split camel case, collapse and trim
  return internalName
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Extracts all internal game mode names from a map of internal → display names.
 *
 * @param internalAndDisplay - A Map where the key is the internal name
 *                            and the value is the display name.
 * @returns A list of all unique internal names (keys) from the map.
 */
export function internalDisplayMapToInternalNamesList(
  internalAndDisplay: Map<string, string>
): string[] {
  const internalNames = new Set<string>(); // Use set to ensure unique values

  for (const internal of internalAndDisplay.keys()) {
    internalNames.add(internal);
  }

  return Array.from(internalNames).sort((a, b) => a.localeCompare(b)); // Return as list and sort ascending
}

/**
 * Extracts all display game mode names from a map of internal → display names.
 *
 * @param internalAndDisplay - A Map where the key is the internal name
 *                            and the value is the display name.
 * @returns A list of all unique display names (values) from the map.
 */
export function internalDisplayMapToDisplayNamesList(
  internalAndDisplay: Map<string, string>
): string[] {
  const displayNames = new Set<string>(); // Use set to ensure unique values

  for (const display of internalAndDisplay.values()) {
    displayNames.add(display);
  }

  return Array.from(displayNames).sort((a, b) => a.localeCompare(b)); // Return as list and sort ascending
}
