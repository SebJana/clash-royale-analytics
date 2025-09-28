import type { Card, CardMeta } from "../../types/cards";
import { CardComponent } from "../card/card";
import "./cardFilter.css";

/**
 * Sorts cards by rarity (common, rare, epic, legendary, champion) and then by elixir cost within the same rarity.
 * @param cards - Array of card metadata to sort
 * @returns Sorted array of card metadata
 */
function sortCards(cards: CardMeta[]): CardMeta[] {
  const rarityOrder = ["common", "rare", "epic", "legendary", "champion"];
  const rarityMap = new Map(rarityOrder.map((r, i) => [r, i]));

  return [...cards].sort((a, b) => {
    // 1. Compare (sort by) rarity
    const rarityDiff =
      (rarityMap.get(a.rarity) ?? Infinity) -
      (rarityMap.get(b.rarity) ?? Infinity);

    if (rarityDiff !== 0) return rarityDiff;

    // 2. Within same rarity, compare (sort by) elixirCost
    return a.elixirCost - b.elixirCost; // ascending
  });
}

/**
 * Creates a Card object with the specified ID and evolution level.
 * @param cardId - The unique identifier for the card
 * @param cardEvolutionLevel - The evolution level of the card (0 for regular cards)
 * @returns A Card object with the specified properties
 */
function createCard(cardId: number, cardEvolutionLevel: number): Card {
  const card: Card = {
    name: "dummy", // name is irrelevant to the card display
    id: cardId,
  };

  if (cardEvolutionLevel > 0) {
    card.evolutionLevel = cardEvolutionLevel;
  }

  return card;
}

/**
 * Creates a list of Card objects from card metadata, including both evolution and regular versions.
 * Evolution cards are added first, followed by regular versions of all cards.
 * @param cards - Array of card metadata to process
 * @returns Array of Card objects including both evolved and regular versions
 */
function createCardList(cards: CardMeta[]): Card[] {
  const cardList: Card[] = [];

  // All cards that have an evolution
  for (const card of cards) {
    const maxEvoLvl = card.maxEvolutionLevel ?? 0;
    if (maxEvoLvl > 0) {
      // NOTE if evolutions ever end up getting another level, this has to be changed
      const c = createCard(card.id, 1);
      cardList.push(c);
    }
  }

  // All regular cards
  for (const card of cards) {
    const c = createCard(card.id, 0);
    cardList.push(c);
  }

  return cardList;
}

export function CardFilter({
  cards,
}: // selected,
// onChange,
Readonly<{
  cards: CardMeta[];
  // selected: Card[];
  // onChange: (next: Card[]) => void; // emit card tuple
}>) {
  const sortedCards = sortCards(cards);
  const cardOptions = createCardList(sortedCards);

  return (
    <div className="card-filter-component-grid">
      {cardOptions.map((c, i) => (
        <CardComponent
          key={`${c.id}-${i}`}
          card={c}
          cards={cards ?? []}
          showTooltip={false}
        />
      ))}
    </div>
  );
}
