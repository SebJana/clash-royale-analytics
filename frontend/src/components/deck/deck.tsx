import { memo } from "react";
import { CardComponent } from "../card/card";
import { getCardElixirCost } from "../../utils/getCardMetaFields";
import type { Card } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";
import { round } from "../../utils/round";
import "./deck.css";

function calcAverageElixirCost(deck: Card[], cards: CardMeta[]) {
  let elixirSum = 0;
  const numberOfCards = deck.length;

  if (numberOfCards < 0) {
    return 0;
  }

  for (const card of deck) {
    elixirSum += getCardElixirCost(card.id, cards);
  }
  const avgElixr = elixirSum / numberOfCards;
  return avgElixr;
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
  const roundedAvgElixir = round(averageElixir, 2);
  // TODO add copy deck option that displays a qr code (desktop) and a direct link (mobile)
  // clashroyale://copyDeck?deck=26000063;27000010;26000067;26000068;26000025;28000001;28000012;26000084&tt=159000000&l=Royals
  // IDs of the cards plus optional tt (timestamp?) and l (label) tag
  return (
    <>
      <div>{rows}</div>
      <p>{roundedAvgElixir}</p>
    </>
  );
});
