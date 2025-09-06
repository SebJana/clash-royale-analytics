import { fetchAllCards } from "./services/cards";
import { useFetch } from "./hooks/useFetch";
import type { Card } from "./types/cards";
import './App.css'

function App() {
  const { data: cards, loading, error } = useFetch<Card[]>(fetchAllCards, []);

  if (loading) return <p>Loading…</p>;
  if (error) return <p>Error loading cards</p>;

  return (
    <ul>
      {cards?.map((c) => (
        <li key={c.id}>{c.name} ({c.elixirCost} elixir)</li>
      ))}
    </ul>
  );
}

export default App
