import { CardComponent } from "../card/card";
import type { Card } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";

export function DeckComponent({
  deck,
  cards,
}: Readonly<{
  deck: Card[];
  cards: CardMeta[];
}>) {
  return (
    <div>
      {deck.map((c, i) => (
        <CardComponent
          key={`${i}-${c.id}`} // unique ID for each card
          card={c}
          cards={cards ?? []} // fall back to empty list, if cards don't exist
        />
      ))}
      {/* TODO add copy deck option that displays a qr code (desktop) and a direct link (mobile)
       clashroyale://copyDeck?deck=26000063;27000010;26000067;26000068;26000025;28000001;28000012;26000084&tt=159000000&l=Royals
       IDs of the cards plus optional tt (timestamp?) and l (label) tag
      */}
    </div>
  );
}
