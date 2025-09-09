import { DeckComponent } from "../deck/deck";
import type { Battle } from "../../types/lastBattles";
import type { CardMeta } from "../../types/cards";
import { datetimeToLocale } from "../../utils/datetimeToLocale";
import "./battle.css";

export function BattleComponent({
  battle,
  cards,
}: Readonly<{
  battle: Battle;
  cards: CardMeta[];
}>) {
  return (
    <div className="battle-component-container">
      <h2>
        {battle.gameMode} — {datetimeToLocale(battle.battleTime)} —{" "}
        {battle.gameResult}
      </h2>
      <div className="battle-component-decks">
        <div className="battle-component-col battle-component-team">
          <h3 className="battle-component-heading">Team</h3>
          {battle.team?.map((t, i) => (
            <section
              key={`${battle.battleTime}-team-${t.tag ?? i}`}
              className="battle-component-player-block"
            >
              <h3 className="battle-component-player-name">
                {t.name ?? `Player ${i + 1}`}
              </h3>
              <DeckComponent deck={t.cards ?? []} cards={cards ?? []} />
            </section>
          ))}
        </div>

        <div className="battle-component-col battle-component-opponent">
          <h3 className="battle-component-heading">Opponent</h3>
          {battle.opponent?.map((o, i) => (
            <section
              key={`${battle.battleTime}-opp-${o.tag ?? i}`}
              className="battle-component-player-block"
            >
              <h3 className="battle-component-player-name">
                {o.name ?? `Player ${i + 1}`}
              </h3>
              <DeckComponent deck={o.cards ?? []} cards={cards ?? []} />
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
