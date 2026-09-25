/**
 * Checks for one leading '#', 4-12 tag characters, and the Supercell alphabet.
 * Does NOT check if the tag exists.
 *
 * @param playerTag - The player tag starting with '#' (e.g., "#YYRJQY28")
 * @returns True if valid, false otherwise
 */
export function validatePlayerTagSyntax(playerTag: string): boolean {
  const ALPHABET = new Set("0289PYLQGRJCUV"); // Supercell-Tag-Alphabet

  // Trim whitespace
  const tag = playerTag.trim();

  if (!tag.startsWith("#") || tag.slice(1).includes("#")) {
    return false;
  }

  const core = tag.slice(1); // Part without the leading '#'
  // NOTE match the backend's current 4-12 limit. Update both validators if Clash
  // Royale starts (or already is) issuing shorter or longer tags.
  if (core.length < 4 || core.length > 12) {
    return false;
  }

  // Every char must be in the possible alphabet
  // Also minimizes injection risk, because special characters won't pass the check
  for (const ch of core) {
    if (!ALPHABET.has(ch)) {
      return false;
    }
  }

  return true;
}
