import type { Card } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";
import {
  getCardName,
  getCardElixirCost,
  getCardRarity,
  getCardIcon,
} from "../../utils/getCardMetaFields";

export function CardComponent({
  card,
  cards,
}: Readonly<{
  card: Card;
  cards: CardMeta[];
}>) {
  return (
    <div>
      <img
        // Display the evolution card icon
        src={getCardIcon(card.id, (card.evolutionLevel ?? 0) > 0, cards)}
        alt={getCardName(card.id, cards)}
        loading="lazy"
      />
      <p>
        {getCardName(card.id, cards)} — {card.level} —{" "}
        {getCardElixirCost(card.id, cards)} — {getCardRarity(card.id, cards)}
      </p>
    </div>
  );
}
