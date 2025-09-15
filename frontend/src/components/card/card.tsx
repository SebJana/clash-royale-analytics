import { memo } from "react";
import Tooltip from "@mui/material/Tooltip";
import type { Card } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";
import { determineRarityOutlineColor } from "../../utils/color";
import {
  getCardName,
  getCardElixirCost,
  getCardRarity,
  getCardIcon,
} from "../../utils/getCardMetaFields";
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
  const outlineColor = determineRarityOutlineColor(rarity, isEvo);

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
        <img
          src={icon}
          alt={name}
          loading="lazy"
          className="card-component-icon"
          style={{
            // Create full outline around PNG shape by using layered drop shadows
            filter: `drop-shadow(1px 0 0 ${outlineColor})
             drop-shadow(-1px 0 0 ${outlineColor})
             drop-shadow(0 1px 0 ${outlineColor})
             drop-shadow(0 -1px 0 ${outlineColor})
             drop-shadow(1px 1px 0 ${outlineColor})
             drop-shadow(-1px -1px 0 ${outlineColor})
             drop-shadow(1px -1px 0 ${outlineColor})
             drop-shadow(-1px 1px 0 ${outlineColor})`,
          }}
        />
      </Tooltip>

      <p className="card-component-level-label">Level {card.level}</p>
    </div>
  );
});
