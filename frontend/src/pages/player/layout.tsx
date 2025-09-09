import { Outlet, NavLink, useParams } from "react-router-dom";
import { usePlayerProfile } from "../../hooks/usePlayerProfile";

export default function PlayerLayout() {
  const { playerTag = "" } = useParams();
  const encodedTag = encodeURIComponent(playerTag ?? "");

  const {
    data: player,
    isLoading: playerLoading,
    isError: isPlayerError,
    error: playerError,
  } = usePlayerProfile(playerTag ?? "");

  if (playerLoading) return <p>Loading…</p>;
  if (isPlayerError)
    return <p>Error loading player profile: {playerError.message}</p>;

  return (
    <div>
      <header>
        <h2>{player?.name}</h2>
      </header>
      <nav style={{ display: "flex", gap: "1rem" }}>
        <NavLink to={`/player/${encodedTag}/battles`}>Battles</NavLink>
        <NavLink to={`/player/${encodedTag}/decks`}>Decks</NavLink>
      </nav>
      <Outlet /> {/* displays active subpage */}
    </div>
  );
}
