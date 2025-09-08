import { useParams } from "react-router-dom";
import { usePlayerBattlesInfinite } from "../../hooks/useLastBattles";

export default function PlayerBattles() {
  const { playerTag = "" } = useParams();
  const {
    data,
    isLoading,
    isError,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = usePlayerBattlesInfinite(playerTag, 5, true);

  const battles = data?.pages.flatMap((p) => p.last_battles.battles) ?? [];

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error: {error.message}</div>;

  return (
    <div>
      <ul>
        {battles.map((b) => (
          <li key={`${b.battleTime}-${b.gameMode}`}>
            {b.gameMode} — {new Date(b.battleTime).toLocaleString()} —{" "}
            {b.gameResult}
          </li>
        ))}
      </ul>

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
