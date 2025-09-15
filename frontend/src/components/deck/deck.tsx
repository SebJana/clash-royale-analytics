import { memo } from "react";
import { CardComponent } from "../card/card";
import { getCardElixirCost } from "../../utils/getCardMetaFields";
import type { Card } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";
import { round } from "../../utils/round";
import { Copy } from "lucide-react";
import "./deck.css";

/**
 * Calculates the average elixir cost of a given deck.
 *
 * @param deck - The list of cards in the deck (each card has an `id`).
 * @param cards - Metadata containing card details including elixir costs.
 * @returns The average elixir cost of the deck, or 0 if the deck is empty.
 *
 */
function calcAverageElixirCost(deck: Card[], cards: CardMeta[]): number {
  let elixirSum = 0;
  const numberOfCards = deck.length;

  if (numberOfCards < 0) {
    return 0;
  }

  for (const card of deck) {
    elixirSum += getCardElixirCost(card.id, cards);
  }
  const avgElixir = elixirSum / numberOfCards;
  return avgElixir;
}

/**
 * Calculates the 4 card cycle elixir cost of a given deck.
 * Effectively sums the elixir cost of the cheapest 4 cards in the deck, meaning
 * the fastest way to get a certain card back into rotation.
 *
 * @param deck - The list of cards in the deck (each card has an `id`).
 * @param cards - Metadata containing card details including elixir costs.
 * @returns The average elixir cost of the deck, or 0 if the deck is NOT 8 cards long.
 *
 */
function calculateFourCardCycle(deck: Card[], cards: CardMeta[]): number {
  const numberOfCards = deck.length;
  // Only calculate 4 Card Cycle for "regular" 8-card decks
  if (numberOfCards !== 8) {
    return 0;
  }
  const elixirAmount = [];
  for (const card of deck) {
    elixirAmount.push(getCardElixirCost(card.id, cards));
  }
  elixirAmount.sort((a, b) => a - b); // Sort elixir amounts ascending

  let fourCardCycle = 0;
  for (let i = 0; i < 4; i++) {
    fourCardCycle += elixirAmount[i]; // Sum the elixir of the cheapest four cards
  }

  return fourCardCycle;
}

/**
 * Builds a Clash Royale deck share link.
 *
 * @param deck - The list of cards in the deck (each card has an `id`).
 * @returns Deck copy link with card IDs and required query params.
 *
 */
function generateCopyLink(deck: Card[]): string {
  const baseURL =
    "https://link.clashroyale.com/en/?clashroyale://copyDeck?deck=";
  let queryParam = baseURL;
  for (const card of deck) {
    queryParam += card.id; // Append the card id for every card in the deck
    queryParam += ";";
  }
  // Remove the trailing ";" for the last card id
  queryParam = queryParam.slice(0, -1);
  // Add necessary fields for the link
  const context = "&l=Royals";
  const timeToken = "&tt=159000000";
  const fullQueryParam = queryParam + context + timeToken;

  return fullQueryParam;
}

export const DeckComponent = memo(function DeckComponent({
  deck,
  cards,
}: Readonly<{
  deck: Card[];
  cards: CardMeta[];
}>) {
  const cardsPerRow = 4;
  const rows: React.ReactElement[] = [];
  for (let i = 0; i < deck.length; i += cardsPerRow) {
    const group = deck.slice(i, i + cardsPerRow); // put the cards into one row of display
    rows.push(
      <div key={`row-${i}`} className="deck-component-deck-row">
        {group.map((card) => (
          <CardComponent key={card.id} card={card} cards={cards} />
        ))}
      </div>
    );
  }

  const averageElixir = calcAverageElixirCost(deck, cards);
  const roundedAvgElixir = round(averageElixir, 1);

  const fourCardCycle = calculateFourCardCycle(deck, cards);
  const roundedFourCardCycle = round(fourCardCycle, 2);

  const copyLink = generateCopyLink(deck);

  // Works for both mobile and desktop because the Clash Royale Website handles
  // showing a qr code (desktop) and a copy link (mobile)
  const handleCopy = () => {
    window.open(copyLink, "_blank");
  };

  return (
    <>
      <div>{rows}</div>
      <div className="deck-component-footer">
        <p>{roundedAvgElixir}</p>
        <p>{roundedFourCardCycle}</p>
        <Copy className="deck-component-copy-button" onClick={handleCopy} />
      </div>
    </>
  );
});
