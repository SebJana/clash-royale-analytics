import { Outlet, NavLink, useParams, useLocation } from "react-router-dom";
import { usePlayerProfile } from "../../hooks/usePlayerProfile";
import { House, Menu, X } from "lucide-react";
import { PlayerInfo } from "../../components/playerInfo/playerInfo";
import { useEffect, useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import "./layout.css";

export default function PlayerLayout() {
  const { playerTag = "" } = useParams();
  const [menuOpen, setMenuOpen] = useState(false);
  const encodedTag = encodeURIComponent(playerTag ?? "");
  const { pathname } = useLocation();

  // Close menu after navigation
  useEffect(() => setMenuOpen(false), [pathname]);

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

        {/* Hamburger Button nur auf Mobile sichtbar */}
        <button className="nav-toggle" onClick={() => setMenuOpen((v) => !v)}>
          {menuOpen ? <X /> : <Menu />}
        </button>

        {/* Menü: Desktop = inline, Mobile = Dropdown/Drawer */}
        <div
          id="player-nav-menu"
          className={`nav-section nav-pages ${menuOpen ? "is-open" : ""}`}
          role="menu"
        >
          <NavLink
            to={`/player/${encodedTag}/battles`}
            className="nav-link"
            role="menuitem"
          >
            Battles
          </NavLink>
          <NavLink
            to={`/player/${encodedTag}/decks`}
            className="nav-link"
            role="menuitem"
          >
            Decks
          </NavLink>
          <NavLink
            to={`/player/${encodedTag}/cards`}
            className="nav-link"
            role="menuitem"
          >
            Cards
          </NavLink>
          <NavLink
            to={`/player/${encodedTag}/stats`}
            className="nav-link"
            role="menuitem"
          >
            Stats
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
