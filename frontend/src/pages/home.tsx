import { useEffect, useState } from "react";
import { LockKeyhole, LockKeyholeOpen, CircleCheck } from "lucide-react";
import { useNavigate } from "react-router";
import {
  fetchAllTrackedPlayers,
  fetchAllTrackedPlayersCount,
  trackPlayer,
  untrackPlayer,
} from "../services/api/trackedPlayers";
import { fetchTotalBattleCount } from "../services/api/battles";
import { pluralize } from "../utils/plural";
import { formatNumberWithSuffix } from "../utils/number";
import { validatePlayerTagSyntax } from "../utils/playerTag";
import { useFetch } from "../hooks/useFetch";
import { useAuth } from "../hooks/useAuthHook";
import type { Players, PlayerCount } from "../types/players";
import type { TotalBattleCount } from "../types/battles";
import { PlayerSearch } from "../components/playerSearch/playerSearch";
import { AuthModal } from "../components/auth/authModal";
import Lottie from "lottie-react";
import construction from "../assets/animations/construction.json";
import CircularProgress from "@mui/material/CircularProgress";
import axios from "axios";
import { StatCard } from "../components/statCard/statCard";
import "./home.css";

// TODO [KEY PERFORMANCE IMPROVEMENT] lazy load card images from CDN to page after opening,
// don't let this load block any other loading and rendering tho

function getErrorMessage(error: unknown): string {
  if (
    !axios.isAxiosError<{
      detail?: string | { code?: string; message?: string };
    }>(error)
  ) {
    return error instanceof Error
      ? error.message
      : "Something went wrong. Please try again.";
  }

  if (!error.response) return "Could not reach the server. Please try again.";

  const { status, data } = error.response;
  const detail = data?.detail;
  const code = typeof detail === "object" ? detail?.code : undefined;

  // Check the backend code first; a 502 can also come from Clash Royale.
  if (code === "INVALID_PLAYER_TAG")
    return "Invalid player tag. Enter a tag like #YYRJQY28.";
  if (code === "PLAYER_NOT_FOUND")
    return "Player not found. Check the tag and try again.";
  if (code === "PLAYER_NOT_TRACKED") return "That player isn't being tracked.";
  if (code === "CR_API_AUTH_FAILED")
    return (
      "Clash Royale rejected the API connection, so this player can't be tracked right now. " +
      "Please try again later."
    );
  if (code === "CR_API_MAINTENANCE")
    return (
      "Clash Royale is currently undergoing maintenance, so this player can't be tracked right now. " +
      "Please try again later."
    );
  if (code === "CR_API_UNAVAILABLE" || code === "CR_API_INVALID_RESPONSE")
    return "Could not check the player with Clash Royale. Please try again later.";
  if (status === 401 || status === 403)
    return "Authorization failed. Please verify again.";
  if (status === 429) return "Too many requests. Please try again shortly.";
  if (status >= 500)
    return "The server could not complete the request. Please try again later.";

  return (
    (typeof detail === "string" ? detail : detail?.message) ??
    "Something went wrong. Please try again."
  );
}

function HomePage() {
  const {
    data: players,
    loading: playersLoading,
    error: playersError,
  } = useFetch<Players>(fetchAllTrackedPlayers, []);

  const {
    data: playerCount,
    loading: playerCountLoading,
    error: playerCountError,
  } = useFetch<PlayerCount>(fetchAllTrackedPlayersCount, []);

  const {
    data: battleCount,
    loading: battleCountLoading,
    error: battleCountError,
  } = useFetch<TotalBattleCount>(fetchTotalBattleCount, []);

  const [selectedPlayerTag, setSelectedPlayerTag] = useState("");
  const [addedPlayerTag, setAddedPlayerTag] = useState("");
  const [untrackedPlayerTag, setUntrackedPlayerTag] = useState("");
  const [trackingPlayer, setTrackingPlayer] = useState(false);
  const [untrackingPlayer, setUntrackingPlayer] = useState(false);
  const [trackingError, setTrackingError] = useState<string | null>(null);
  const [untrackingError, setUntrackingError] = useState<string | null>(null);
  const [trackingSuccess, setTrackingSuccess] = useState<string | null>(null);
  const [untrackingSuccess, setUntrackingSuccess] = useState<string | null>(
    null,
  );
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showAuthSuccess, setShowAuthSuccess] = useState(false);
  const navigate = useNavigate();
  const { isAuthenticated, checkAuthStatus } = useAuth();

  useEffect(() => {
    if (!showAuthSuccess) return;
    const timer = window.setTimeout(() => setShowAuthSuccess(false), 5000);
    return () => window.clearTimeout(timer);
  }, [showAuthSuccess]);

  if (playersLoading || playerCountLoading || battleCountLoading)
    return <CircularProgress className="home-loading-spinner" />;
  if (playersError || playerCountError || battleCountError)
    return (
      <>
        <Lottie
          animationData={construction}
          loop={true}
          className="lottie-animation"
        />
        <h2 className="home-fatal-error-message">
          We're having trouble right now. Please try again shortly.
        </h2>
      </>
    );

  const playerList = players
    ? Object.entries(players.activePlayers).map(([tag, name]) => ({
        tag,
        name,
      }))
    : [];

  function canEnableViewButton() {
    /**
     * Helper function to check if the view button should be able to be clickable
     */
    if (!selectedPlayerTag) {
      return false;
    }
    if (!validatePlayerTagSyntax(selectedPlayerTag)) {
      return false;
    }
    return true;
  }

  const handleViewClick = () => {
    if (selectedPlayerTag) {
      // Navigate user to the selected player profile page
      navigate(`/player/${encodeURIComponent(selectedPlayerTag)}/battles`);
    }
  };

  const handleAddPlayerClick = async () => {
    if (!addedPlayerTag) return;

    setTrackingPlayer(true);
    setTrackingError(null);
    setTrackingSuccess(null);

    try {
      const result = await trackPlayer(addedPlayerTag);
      setTrackingSuccess(`${result.status}: ${result.tag}`);

      // Clear the input field
      setAddedPlayerTag("");
    } catch (error) {
      setTrackingError(getErrorMessage(error));
    } finally {
      setTrackingPlayer(false);
    }
  };

  const handleUntrackPlayerClick = async () => {
    if (!untrackedPlayerTag) return;
    if (!validatePlayerTagSyntax(untrackedPlayerTag)) {
      setUntrackingError("Invalid player tag. Enter a tag like #YYRJQY28.");
      setUntrackingSuccess(null);
      return;
    }
    setUntrackingError(null);

    // Check if user is authenticated
    if (!checkAuthStatus()) {
      setShowAuthModal(true);
      return;
    }

    setUntrackingPlayer(true);
    setUntrackingSuccess(null);

    try {
      const result = await untrackPlayer(untrackedPlayerTag);
      setUntrackingSuccess(`${result.status}: ${result.tag}`);

      // Clear the input field
      setUntrackedPlayerTag("");
    } catch (error) {
      setUntrackingError(getErrorMessage(error));
    } finally {
      setUntrackingPlayer(false);
    }
  };

  const handleAuthSuccess = () => {
    setShowAuthModal(false);
    setShowAuthSuccess(true);
    setUntrackingError(null);
    setUntrackingSuccess(null);
  };

  return (
    <div className="home-page">
      <div className="home-container">
        <div className="home-header">
          <img
            src="/crown.png"
            alt="Clash Royale Crown"
            className="home-icon"
          />
          <h1 className="home-title">Clash Royale Analytics</h1>
          <div className="home-stat-cards-container">
            <StatCard
              value={formatNumberWithSuffix(
                playerCount?.activePlayerCount ?? 0,
              )}
              label={`Tracked ${pluralize(
                playerCount?.activePlayerCount ?? 0,
                "Player",
                "Players",
              )}`}
            />
            <StatCard
              value={formatNumberWithSuffix(battleCount?.totalBattleCount ?? 0)}
              label={`${pluralize(
                playerCount?.activePlayerCount ?? 0,
                "Battle",
                "Battles",
              )} on record`}
            />
          </div>
        </div>
        <div className="player-selection">
          <div className="search-section">
            <h2 className="section-header">View Players</h2>
            <p className="section-description">
              Search and view analytics for players already being tracked in our
              system.
            </p>
            <PlayerSearch
              players={playerList}
              selectedPlayerTag={selectedPlayerTag}
              onSelectPlayer={(player) => setSelectedPlayerTag(player.tag)}
            />
            <button
              className="view-button"
              onClick={handleViewClick}
              disabled={!canEnableViewButton()}
            >
              View Player
            </button>
          </div>
          <div className="adding-section">
            <h2 className="section-header">Add New Player</h2>
            <p className="section-description">
              Enter a player tag to start tracking their battles, decks, and
              performance analytics.
            </p>
            <input
              type="text"
              placeholder="Enter player tag... (e.g. #YYRJQY28)"
              value={addedPlayerTag}
              onChange={(e) => setAddedPlayerTag(e.target.value)}
            />
            <button
              className="add-button"
              onClick={handleAddPlayerClick}
              disabled={!addedPlayerTag || trackingPlayer}
            >
              {trackingPlayer ? "Adding Player..." : "Add Player"}
            </button>

            {trackingError && (
              <div className="home-error-message">{trackingError}</div>
            )}

            {trackingSuccess && (
              <div className="home-success-message">{trackingSuccess}</div>
            )}
          </div>
          <div
            className={`untrack-section${showAuthSuccess && isAuthenticated ? " untrack-section-unlocked" : ""}`}
          >
            <h2 className="section-header">
              Remove Tracked Player
              <span
                className={`untrack-auth-status${isAuthenticated ? " is-unlocked" : ""}`}
                role="img"
                aria-label={
                  isAuthenticated ? "Verified" : "Verification required"
                }
                title={isAuthenticated ? "Verified" : "Verification required"}
              >
                <span className="untrack-auth-icon" aria-hidden="true">
                  {isAuthenticated ? (
                    <LockKeyholeOpen size={24} />
                  ) : (
                    <LockKeyhole size={24} />
                  )}
                </span>
              </span>
            </h2>
            <p className="section-description">
              {isAuthenticated
                ? "Enter a player tag to stop tracking their activity."
                : "Verify to stop tracking a player's activity."}{" "}
              Previously stored data won't be deleted by this, you can always
              add the player back.
            </p>
            {isAuthenticated ? (
              <>
                <input
                  type="text"
                  aria-label="Player tag to remove"
                  placeholder="Enter player tag... (e.g. #YYRJQY28)"
                  value={untrackedPlayerTag}
                  onChange={(e) => {
                    const tag = e.target.value;
                    setUntrackedPlayerTag(tag);
                    if (validatePlayerTagSyntax(tag)) setUntrackingError(null);
                  }}
                />
                <button
                  className="remove-button"
                  onClick={handleUntrackPlayerClick}
                  disabled={!untrackedPlayerTag || untrackingPlayer}
                >
                  {untrackingPlayer ? "Removing Player..." : "Remove Player"}
                </button>
              </>
            ) : (
              <button
                className="verify-remove-button"
                onClick={() => setShowAuthModal(true)}
              >
                Verify
              </button>
            )}

            <div
              className="untrack-auth-feedback"
              role="status"
              aria-atomic="true"
            >
              {showAuthSuccess && isAuthenticated && (
                <div className="home-success-message untrack-auth-success">
                  <CircleCheck size={20} aria-hidden="true" />
                  <span>
                    Verification complete! Enter a player tag to remove.
                  </span>
                </div>
              )}
            </div>

            {untrackingError && (
              <div className="home-error-message">{untrackingError}</div>
            )}

            {untrackingSuccess && (
              <div className="home-success-message">{untrackingSuccess}</div>
            )}
          </div>
        </div>

        <AuthModal
          open={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          onSuccess={handleAuthSuccess}
        />
      </div>
    </div>
  );
}

export default HomePage;
