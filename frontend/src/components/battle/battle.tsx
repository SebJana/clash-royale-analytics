import { DeckComponent } from "../deck/deck";
import type { Battle } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";
import { datetimeToLocale } from "../../utils/datetimeToLocale";

export function BattleComponent({
  battle,
  cards,
}: Readonly<{
  battle: Battle;
  cards: CardMeta[];
}>) {
  return (
    <>
      <h2>
        {battle.gameMode} — {datetimeToLocale(battle.battleTime)} —{" "}
        {battle.gameResult}
      </h2>
      <div>
        {battle.team.map((t, i) => (
          <>
            <h3>{t.name}</h3>
            <DeckComponent
              key={`${i}-${t.tag}-${battle.battleTime}`} // unique ID for each battle
              deck={t.cards ?? []}
              cards={cards ?? []} // fall back to empty list, if cards don't exist
            />
          </>
        ))}
      </div>
      <div>
        {battle.opponent.map((o, i) => (
          <>
            <h3>{o.name}</h3>
            <DeckComponent
              key={`${i}-${o.tag}-${battle.battleTime}`} // unique ID for each battle
              deck={o.cards ?? []}
              cards={cards ?? []} // fall back to empty list, if cards don't exist
            />
          </>
        ))}
      </div>
    </>
  );
}
