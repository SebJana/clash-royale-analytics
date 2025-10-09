import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/home";
import PlayerLayout from "./pages/player/layout";
import PlayerDecks from "./pages/player/decks";
import PlayerBattles from "./pages/player/battles";
import PlayerCards from "./pages/player/cards";
import PlayerStats from "./pages/player/stats";
import "./App.css";

function App() {
  return (
    <main className="main-container">
      <Routes>
        <Route path="/" element={<HomePage />} />

        <Route path="/player/:playerTag" element={<PlayerLayout />}>
          <Route index element={<PlayerBattles />} />
          <Route path="battles" element={<PlayerBattles />} />
          <Route path="decks" element={<PlayerDecks />} />
          <Route path="cards" element={<PlayerCards />} />
          <Route path="stats" element={<PlayerStats />} />
        </Route>
      </Routes>
    </main>
  );
}

export default App;
