import { useState } from "react";
import { useNavigate } from "react-router";
import { fetchAllTrackedPlayers } from "../../services/api/trackedPlayers";
import { validatePlayerTagSyntax } from "../../utils/playerTag";
import { useFetch } from "../../hooks/useFetch";
import { useCards } from "../../hooks/useCards";
import type { Players } from "../../types/players";
import { PlayerSearch } from "../../components/playerSearch/playerSearch";

function HomePage() {
  const {
    data: cards,
    isLoading: cardsLoading,
    isError: cardsError,
  } = useCards();
  const {
    data: players,
    loading: playersLoading,
    error: playersError,
  } = useFetch<Players>(fetchAllTrackedPlayers, []);
  const [selectedPlayerTag, setSelectedPlayerTag] = useState("");
  const navigate = useNavigate();

  if (cardsLoading || playersLoading) return <p>Loading…</p>;
  if (cardsError || playersError) return <p>Error loading</p>;

  const playerList = players
    ? Object.entries(players.activePlayers).map(([tag, name]) => ({
        tag,
        name,
      }))
    : [];

  // Temporary cards for debug on homepage
  cards?.forEach((c) => {
    console.log(`${c.name} (${c.elixirCost} elixir)`);
  });

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
      navigate(`/player/${encodeURIComponent(selectedPlayerTag)}`);
    }
  };

  return (
    <section>
      <h2>Select a player</h2>
      <PlayerSearch
        players={playerList}
        selectedPlayerTag={selectedPlayerTag}
        onSelectPlayer={(player) => setSelectedPlayerTag(player.tag)}
      />
      <button onClick={handleViewClick} disabled={!canEnableViewButton()}>
        View
      </button>
    </section>
  );
}

export default HomePage;
