import { Outlet, NavLink, useParams } from "react-router-dom";
import { useEffect } from "react";
import { useCards } from "../../hooks/useCards";
import { usePlayerProfile } from "../../hooks/usePlayerProfile";

export default function PlayerLayout() {
  const { playerTag = "" } = useParams();
  const encodedTag = encodeURIComponent(playerTag ?? "");

  const {
    data: cards,
    isLoading: cardsLoading,
    isError: isCardsError,
    error: cardsError,
  } = useCards();

  const {
    data: player,
    isLoading: playerLoading,
    isError: isPlayerError,
    error: playerError,
  } = usePlayerProfile(playerTag ?? "");

  // Temporary cards debug
  useEffect(() => {
    cards?.forEach((c) => console.log(`${c.name} (${c.elixirCost} elixir)`));
  }, [cards]);

  if (cardsLoading || playerLoading) return <p>Loading…</p>;
  if (isCardsError) return <p>Error loading cards: {cardsError.message}</p>;
  if (isPlayerError)
    return <p>Error loading player profile: {playerError.message}</p>;

  return (
    <div>
      <header>
        <h2>{player?.name}</h2>
      </header>
      <nav style={{ display: "flex", gap: "1rem" }}>
        <NavLink to={`/player/${encodedTag}/battles`}>Battles</NavLink>
        <NavLink to={`/player/${encodedTag}/decks`}>Decks</NavLink>
      </nav>
      <Outlet /> {/* displays active subpage */}
    </div>
  );
}
