import { useEffect } from "react";
import type { Battle } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";

export function Battle({
  battle,
  cards,
}: Readonly<{
  battle: Battle;
  cards: CardMeta[];
}>) {
  useEffect(() => {
    cards?.forEach((c) => console.log(`${c.name} (${c.elixirCost} elixir)`));
  }, [cards]);

  return (
    <div>
      {battle.gameMode} — {new Date(battle.battleTime).toLocaleString()} —{" "}
      {battle.gameResult}
    </div>
  );
}
