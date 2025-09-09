import { CardComponent } from "../card/card";
import type { Card } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";
import "./deck.css";

export function DeckComponent({
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
      <div key={`row-${i}`} className="deck-component-deckRow">
        {group.map((card) => (
          <CardComponent key={card.id} card={card} cards={cards} />
        ))}
      </div>
    );
  }
  // TODO add copy deck option that displays a qr code (desktop) and a direct link (mobile)
  // clashroyale://copyDeck?deck=26000063;27000010;26000067;26000068;26000025;28000001;28000012;26000084&tt=159000000&l=Royals
  // IDs of the cards plus optional tt (timestamp?) and l (label) tag
  return <div>{rows}</div>;
}
