import { Outlet, NavLink, useParams } from "react-router-dom";
import { usePlayerProfile } from "../../hooks/usePlayerProfile";
import { PlayerInfo } from "../../components/playerInfo/playerInfo";
import CircularProgress from "@mui/material/CircularProgress";
import "./layout.css";

export default function PlayerLayout() {
  const { playerTag = "" } = useParams();
  const encodedTag = encodeURIComponent(playerTag ?? "");

  const {
    data: player,
    isLoading: playerLoading,
    isError: isPlayerError,
    error: playerError,
  } = usePlayerProfile(playerTag ?? "");

  if (playerLoading)
    return <CircularProgress className="layout-loading-spinner" />;
  if (isPlayerError)
    return <p>Error loading player profile: {playerError.message}</p>;

  return (
    <div className="player-layout">
      <header className="player-header">
        {/* Only render player info if there is a valid player fetched */}
        {player && <PlayerInfo player={player} />}
      </header>
      <nav className="player-nav" style={{ display: "flex", gap: "1rem" }}>
        <NavLink to={`/player/${encodedTag}/battles`}>Battles</NavLink>
        <NavLink to={`/player/${encodedTag}/decks`}>Decks</NavLink>
      </nav>
      <main className="player-content">
        <Outlet /> {/* displays active subpage */}
      </main>
    </div>
  );
}
