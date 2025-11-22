import { useState } from "react";
import { useNavigate } from "react-router";
import {
  fetchAllTrackedPlayers,
  trackPlayer,
} from "../services/api/trackedPlayers";
import { validatePlayerTagSyntax } from "../utils/playerTag";
import { useFetch } from "../hooks/useFetch";
import type { Players } from "../types/players";
import { PlayerSearch } from "../components/playerSearch/playerSearch";
import "./home.css";

function HomePage() {
  const {
    data: players,
    loading: playersLoading,
    error: playersError,
  } = useFetch<Players>(fetchAllTrackedPlayers, []);

  const [selectedPlayerTag, setSelectedPlayerTag] = useState("");
  const [addedPlayerTag, setAddedPlayerTag] = useState("");
  const [trackingPlayer, setTrackingPlayer] = useState(false);
  const [trackingError, setTrackingError] = useState<string | null>(null);
  const [trackingSuccess, setTrackingSuccess] = useState<string | null>(null);
  const navigate = useNavigate();

  if (playersLoading) return <p>Loading…</p>;
  if (playersError) return <p>Error loading</p>;

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
      // Extract error message using structural typing
      type ErrorLike = {
        response?: { data?: { detail?: string } };
        message?: string;
      };

      const err = error as ErrorLike;
      // See if there is any error text or status message on what happened upon error
      const errorDetail =
        err.response?.data?.detail || err.message || "An error occurred";
      setTrackingError(errorDetail);
    } finally {
      setTrackingPlayer(false);
    }
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
              <div className="error-message">{trackingError}</div>
            )}

            {trackingSuccess && (
              <div className="success-message">{trackingSuccess}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
