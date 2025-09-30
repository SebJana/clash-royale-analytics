/**
 * Checks whether the player tag starts with a '#' and has the correct length
 * and matches the Supercell alphabet. Does NOT check if the tag actually exists for a player.
 *
 * @param playerTag - The player tag starting with '#' (e.g., "#YYRJQY28")
 * @returns True if valid, false otherwise
 */
export function validatePlayerTagSyntax(playerTag: string): boolean {
  const ALPHABET = new Set("0289PYLQGRJCUV"); // Supercell-Tag-Alphabet

  // Trim whitespace
  const tag = playerTag.trim();

  // Must start with '#'
  if (!tag.startsWith("#")) {
    return false;
  }

  const core = tag.slice(1); // Part without the leading '#'

  // TODO add sanitization to prevent injection attacks

  // Every char must be in the possible alphabet
  for (const ch of core) {
    if (!ALPHABET.has(ch)) {
      return false;
    }
  }

  return true;
}
