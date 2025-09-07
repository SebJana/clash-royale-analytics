import { fetchAllTrackedPlayers } from "../../services/api/players";
import { useFetch } from "../../hooks/useFetch";
import { useCards } from "../../hooks/useCards";
import type { Players } from "../../types/players";
import { PlayerSearch } from "../../components/playerSearch/playerSearch";

function HomePage() {
  const { data: cards, isLoading: cardsLoading, isError: cardsError } = useCards();
  const { data: players, loading: playersLoading, error: playersError } =
    useFetch<Players>(fetchAllTrackedPlayers, []);

  if (cardsLoading || playersLoading) return <p>Loading…</p>;
  if (cardsError || playersError) return <p>Error loading</p>;

  const playerList = players
    ? Object.entries(players.activePlayers).map(([tag, name]) => ({
        tag,
        name,
      }))
    : [];

  cards?.forEach((c) => {
    console.log(`${c.name} (${c.elixirCost} elixir)`);
  });

  
  return (
    <section>
        <h2>Select a player</h2>
        <PlayerSearch players={playerList} />
    </section>
  );
}

export default HomePage;
