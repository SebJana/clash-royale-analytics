import type { CardMeta } from "../types/cards";

export function getCardName(cardID: number, cards: CardMeta[]): string {
  return cards.find((c) => c.id === cardID)?.name ?? `#${cardID}`;
}

export function getCardRarity(cardID: number, cards: CardMeta[]): string {
  return cards.find((c) => c.id === cardID)?.rarity ?? `#${cardID}`;
}

export function getCardElixirCost(cardID: number, cards: CardMeta[]): number {
  return cards.find((c) => c.id === cardID)?.elixirCost ?? 0;
}

export function getCardIcon(
  cardID: number,
  evolutionLevel: number,
  cards: CardMeta[]
): string {
  // Return the evolution icon version for the specified card
  if (evolutionLevel === 2) {
    return (
      cards.find((c) => c.id === cardID)?.iconUrls.heroMedium ?? `#${cardID}`
    );
  }
  // Return the evolution icon version for the specified card
  if (evolutionLevel === 1) {
    return (
      cards.find((c) => c.id === cardID)?.iconUrls.evolutionMedium ??
      `#${cardID}`
    );
  }
  // Use the regular icon for the rest
  return cards.find((c) => c.id === cardID)?.iconUrls.medium ?? `#${cardID}`;
}
