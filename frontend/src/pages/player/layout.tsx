import { Outlet, NavLink, useParams, useLocation } from "react-router-dom";
import { usePlayerProfile } from "../../hooks/usePlayerProfile";
import { House, Menu, X, ChevronLeft } from "lucide-react";
import { PlayerInfo } from "../../components/playerInfo/playerInfo";
import { useEffect, useState } from "react";
import Lottie from "lottie-react";
import emptyBox from "../../assets/animations/emptyBox.json";
import genericError from "../../assets/animations/404.json";

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
  if (isPlayerError) {
    console.log(playerError);

    // Check if it's a 403 error (player not found/isn't being tracked)
    // Both by the api backend (403) OR the frontend tag syntax check ("Invalid player tag")
    const errorMessage = playerError?.message || String(playerError);
    const is403Error =
      errorMessage.includes("status code 403") ||
      errorMessage.includes("403") ||
      errorMessage.includes("Invalid player tag");

    const displayMessage = is403Error
      ? "We searched everywhere, but couldn't find the player you were looking for in our system"
      : "Something went wrong while loading the player data. Please try again later.";

    return (
      <div className="layout-error-container">
        {/* Player not found */}
        {is403Error && (
          <Lottie
            animationData={emptyBox}
            loop={true}
            className="lottie-animation"
          />
        )}
        {/* Generic backend issue (running, network, token, ...) */}
        {!is403Error && (
          <Lottie
            animationData={genericError}
            loop={true}
            className="lottie-animation"
          />
        )}
        <h2 className="layout-error-message">{displayMessage}</h2>
        <NavLink to={`/`} className="nav-link">
          <ChevronLeft />
          Back to Home
        </NavLink>
      </div>
    );
  }

  return (
    <div className="player-layout">
      <nav className="player-nav-container">
        <div className="nav-section nav-home">
          <NavLink to={`/`} className="nav-link">
            <House />
            Home
          </NavLink>
        </div>

        {/* Only show on mobile */}
        <button className="nav-toggle" onClick={() => setMenuOpen((v) => !v)}>
          {menuOpen ? <X /> : <Menu />}
        </button>

        {/* Page menu: Desktop = inline, Mobile = Dropdown */}
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
            to={`/player/${encodedTag}/plots`}
            className="nav-link"
            role="menuitem"
          >
            Plots
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
