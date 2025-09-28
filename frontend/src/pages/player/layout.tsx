import { Outlet, NavLink, useParams } from "react-router-dom";
import { usePlayerProfile } from "../../hooks/usePlayerProfile";
import { PlayerInfo } from "../../components/playerInfo/playerInfo";
import { House } from "lucide-react";
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
      <nav className="player-nav-container">
        <div className="nav-section nav-home">
          <NavLink to={`/`} className="nav-link">
            <House />
            Home
          </NavLink>
        </div>
        <div className="nav-section nav-pages">
          <NavLink to={`/player/${encodedTag}/battles`} className="nav-link">
            Battles
          </NavLink>
          <NavLink to={`/player/${encodedTag}/decks`} className="nav-link">
            Decks
          </NavLink>
        </div>
      </nav>
      <header className="player-header">
        {/* Only render player info if there is a valid player fetched */}
        {player && <PlayerInfo player={player} />}
      </header>
      <main className="player-content">
        <Outlet /> {/* displays active subpage */}
      </main>
    </div>
  );
}
