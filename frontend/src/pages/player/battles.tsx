import { useParams } from "react-router-dom";
import { useCards } from "../../hooks/useCards";
import { usePlayerBattlesInfinite } from "../../hooks/useLastBattles";
import { BattleComponent } from "../../components/battle/battle";

export default function PlayerBattles() {
  const { playerTag = "" } = useParams();

  const {
    data: cards,
    isLoading: cardsLoading,
    isError: isCardsError,
    error: cardsError,
  } = useCards();

  const {
    data: battles,
    isLoading: battlesLoading,
    isError: isBattlesError,
    error: battlesError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = usePlayerBattlesInfinite(playerTag, 5, true);

  const battlesList =
    battles?.pages.flatMap((p) => p.last_battles.battles) ?? [];

  if (battlesLoading || cardsLoading) return <div>Loading...</div>;
  if (isCardsError) return <div>Error: {cardsError.message}</div>;
  if (isBattlesError) return <div>Error: {battlesError.message}</div>;

  return (
    <div>
      {battlesList.map((b, i) => (
        <BattleComponent
          key={`${i}-${playerTag}-${b.battleTime}`} // unique ID for each battle
          battle={b}
          cards={cards ?? []} // fall back to empty list, if cards don't exist
        />
      ))}

      {hasNextPage ? (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          {isFetchingNextPage ? "Loading..." : "Load more"}
        </button>
      ) : (
        <div>No more battles</div>
      )}
    </div>
  );
}
