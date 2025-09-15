/**
 * Determines the outline color for a card based on its rarity.
 *
 * - Returns `null` if the card is an evolution (evolutions never have a colored outline).
 * - Returns `null` for "common" cards as well, since they already have a default gray outline.
 * - Returns a hex color string for rarities that use special outlines.
 *
 * @param rarity - The rarity of the card (e.g. "common", "rare", "epic", "legendary", "champion").
 * @param evolution - Whether the card is an evolution; if true, no outline color is returned.
 * @returns A hex color string for the outline, or `null` if no colored outline should be used.
 */
export function determineRarityOutlineColor(
  rarity: string,
  evolution: boolean
): string | null {
  if (evolution) {
    return null;
  }

  const r = rarity.toLowerCase();
  switch (r) {
    case "common":
      return null;
    case "rare":
      return "#fca46b";
    case "epic":
      return "#a149de";
    case "legendary":
      return "#cda2d2";
    case "champion":
      return "#fed328";
    default:
      return null;
  }
}
