import { memo } from "react";
import Tooltip from "@mui/material/Tooltip";
import type { Card, CardMeta } from "../../types/cards";
import {
  getCardName,
  getCardElixirCost,
  getCardRarity,
  getCardIcon,
} from "../../utils/getCardMetaFields";
import { getCardOutline } from "../../utils/color";
import "./card.css";

export const CardComponent = memo(function CardComponent({
  card,
  cards,
}: Readonly<{
  card: Card;
  cards: CardMeta[];
}>) {
  const name = getCardName(card.id, cards);
  const elixir = getCardElixirCost(card.id, cards);
  const rarity = getCardRarity(card.id, cards);
  // Uppercase the first letter of the rarity
  const rarityLabel = rarity
    ? rarity.charAt(0).toUpperCase() + rarity.slice(1)
    : "";
  const evoLvl = card.evolutionLevel ?? 0; // If it's not an evolution, the evolutionLevel field is missing
  const isEvo = evoLvl > 0;
  const icon = getCardIcon(card.id, isEvo, cards);

  const outlineImg = getCardOutline(rarity);

  return (
    <div className="card-component-card">
      <Tooltip
        arrow
        placement="auto"
        title={
          <div className="card-component-tooltip">
            <strong>{name}</strong>
            <span>{elixir} Elixir</span>
            <span>{rarityLabel}</span>
          </div>
        }
      >
        {/* Card outline implemented using overlaid PNG images */}
        <div className="card-component-wrap">
          <img
            src={outlineImg}
            alt={`outline`}
            loading="lazy"
            className="card-component-outline"
          />
          <img
            src={icon}
            alt={name}
            loading="lazy"
            className="card-component-icon"
          />
        </div>
      </Tooltip>

      {/* Only show level label if it exists (Battle page, not for Decks/Cards page) */}
      {card?.level != null && (
        <p className="card-component-level-label">Level {card.level}</p>
      )}
    </div>
  );
});
