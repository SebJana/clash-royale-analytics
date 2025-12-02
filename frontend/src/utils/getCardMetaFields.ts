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

// TODO adjust for evolutionLevel = 2, use number instead of boolean
export function getCardIcon(
  cardID: number,
  evolution: boolean,
  cards: CardMeta[]
): string {
  // Return the evolution icon version for the specified card
  if (evolution) {
    return (
      cards.find((c) => c.id === cardID)?.iconUrls.evolutionMedium ??
      `#${cardID}`
    );
  }
  return cards.find((c) => c.id === cardID)?.iconUrls.medium ?? `#${cardID}`;
}
