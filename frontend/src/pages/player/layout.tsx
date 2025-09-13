import { Outlet, NavLink, useParams } from "react-router-dom";
import { usePlayerProfile } from "../../hooks/usePlayerProfile";
import { PlayerInfo } from "../../components/playerInfo/playerInfo";

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
        {/* Only render player info if there is a valid player fetched */}
        {player && <PlayerInfo player={player} />}
      </header>
      <nav style={{ display: "flex", gap: "1rem" }}>
        <NavLink to={`/player/${encodedTag}/battles`}>Battles</NavLink>
        <NavLink to={`/player/${encodedTag}/decks`}>Decks</NavLink>
      </nav>
      <Outlet /> {/* displays active subpage */}
    </div>
  );
}
