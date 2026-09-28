import { Outlet, NavLink, useParams, useLocation } from "react-router-dom";
import { usePlayerProfile } from "../../hooks/usePlayerProfile";
import { House, Menu, X, ChevronLeft } from "lucide-react";
import { PlayerInfo } from "../../components/playerInfo/playerInfo";
import { PlayerInfoPlaceholder } from "../../components/playerInfo/playerInfoPlaceholder";
import { PlayerErrorBoundary } from "../../components/playerError/playerErrorBoundary";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { fetchAllTrackedPlayers } from "../../services/api/trackedPlayers";
import { pingApi } from "../../services/api/ping";
import Lottie from "lottie-react";
import emptyBox from "../../assets/animations/emptyBox.json";
import genericError from "../../assets/animations/404.json";

import CircularProgress from "@mui/material/CircularProgress";
import "./layout.css";

export default function PlayerLayout() {
  const { playerTag = "" } = useParams();
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileRetryAttempts, setProfileRetryAttempts] = useState(0);
  const encodedTag = encodeURIComponent(playerTag ?? "");
  const { pathname } = useLocation();

  // Close menu after navigation
  useEffect(() => setMenuOpen(false), [pathname]);

  const {
    data: player,
    isLoading: playerLoading,
    isFetched: profileFetched,
    isError: isPlayerError,
    error: playerError,
    errorUpdatedAt: profileErrorUpdatedAt,
    refetch: refetchPlayer,
  } = usePlayerProfile(playerTag ?? "");

  // Keep the count while the placeholder briefly unmounts for a fresh API check.
  useEffect(() => setProfileRetryAttempts(0), [playerTag, player]);

  const errorDetail = axios.isAxiosError<{
    detail?: { code?: string };
  }>(playerError)
    ? playerError.response?.data?.detail
    : undefined;
  // Only invalid and untracked tags need the full-page error.
  const isNotFound =
    playerError?.message === "Invalid player tag" ||
    (axios.isAxiosError(playerError) &&
      playerError.response?.status === 403 &&
      (errorDetail?.code === "INVALID_PLAYER_TAG" ||
        errorDetail?.code === "PLAYER_NOT_TRACKED"));
  const { isError: isApiDown, isSuccess: isApiReachable } = useQuery({
    // Check each profile failure against the current backend state, not an old ping.
    queryKey: ["apiPing", playerTag, profileErrorUpdatedAt],
    queryFn: pingApi,
    enabled: isPlayerError && !isNotFound,
    retry: false,
    staleTime: 0,
    gcTime: 60_000,
    // Keep the placeholder visible while checking the backend again.
    placeholderData: (previousData) => previousData,
  });
  const showProfilePlaceholder =
    !isNotFound &&
    isApiReachable &&
    (isPlayerError || (profileFetched && !player));

  // The tracked-player list can supply the name when the live profile fails.
  const { data: trackedPlayers } = useQuery({
    queryKey: ["trackedPlayers"],
    queryFn: fetchAllTrackedPlayers,
    enabled: showProfilePlaceholder && !player,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });
  const knownName = player?.name ?? trackedPlayers?.activePlayers[playerTag];

  if (playerLoading && !profileFetched)
    return <CircularProgress className="layout-loading-spinner" />;
  if (isPlayerError && !isNotFound && !isApiReachable && !isApiDown)
    return <CircularProgress className="layout-loading-spinner" />;
  if (isPlayerError && (isNotFound || isApiDown)) {
    console.log(playerError);

    const displayMessage = isNotFound
      ? "We searched everywhere, but couldn't find the player you were looking for in our system"
      : "Something went wrong while loading the player data. Please try again later.";

    return (
      <div className="layout-error-container">
        {/* Player not found */}
        {isNotFound && (
          <Lottie
            animationData={emptyBox}
            loop={true}
            className="lottie-animation"
          />
        )}
        {/* Generic backend issue */}
        {!isNotFound && (
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
        {showProfilePlaceholder ? (
          <PlayerInfoPlaceholder
            tag={playerTag}
            name={knownName}
            retry={refetchPlayer}
            retryAttempts={profileRetryAttempts}
            onRetryAttempt={() => setProfileRetryAttempts((count) => count + 1)}
          />
        ) : (
          player && <PlayerInfo player={player} />
        )}
      </header>
      <main className="player-content">
        <PlayerErrorBoundary key={pathname}>
          <Outlet /> {/* displays active subpage */}
        </PlayerErrorBoundary>
      </main>
    </div>
  );
}
