import { useParams } from "react-router-dom";
import { useMemo } from "react";
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
  } = usePlayerBattlesInfinite(playerTag, 3, true);

  const battlesList = useMemo(
    () => battles?.pages.flatMap((p) => p.last_battles.battles) ?? [],
    [battles]
  );

  if (battlesLoading || cardsLoading) return <div>Loading...</div>;
  if (isCardsError) return <div>Error: {cardsError.message}</div>;
  if (isBattlesError) return <div>Error: {battlesError.message}</div>;

  return (
    // TODO add before datetime selector, to filter for specific time
    <div>
      {battlesList.map((b, i) => (
        <BattleComponent
          key={`${b.battleTime}-${playerTag}-${i}`} // More stable unique ID
          battle={b}
          cards={cards ?? []} // fall back to empty list, if cards don't exist
        />
      ))}

      {hasNextPage ? (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          {isFetchingNextPage ? "Loading..." : "Load more"}
        </button>
      ) : (
        // TODO upon reloading with many loaded battles, user sees "No more battles", but should see loading spinner
        <div>No more battles</div>
      )}
    </div>
  );
}
