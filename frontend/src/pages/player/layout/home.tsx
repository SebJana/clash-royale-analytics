import { Outlet, NavLink, useParams } from "react-router-dom";
import { useEffect } from "react";
import { useCards } from "../../../hooks/useCards";

export default function PlayerLayout() {
  const { playerTag } = useParams();
  const encodedTag = encodeURIComponent(playerTag ?? "");

  const {
    data: cards,
    isLoading: cardsLoading,
    isError: cardsError,
  } = useCards();

  // Temporary cards debug
  useEffect(() => {
    cards?.forEach((c) => console.log(`${c.name} (${c.elixirCost} elixir)`));
  }, [cards]);

  if (cardsLoading) return <p>Loading…</p>;
  if (cardsError) return <p>Error loading</p>;

  return (
    <div>
      <header>
        <h2>Player {playerTag}</h2>
      </header>
      <nav style={{ display: "flex", gap: "1rem" }}>
        <NavLink to={`/player/${encodedTag}/battles`}>Battles</NavLink>
        <NavLink to={`/player/${encodedTag}/decks`}>Decks</NavLink>
      </nav>
      <Outlet context={{ playerTag, cards }} /> {/* displays active subpage */}
    </div>
  );
}
