import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/home";
import PlayerLayout from "./pages/player/home";
import PlayerDecks from "./pages/player/decks";
import PlayerBattles from "./pages/player/battles";
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
        </Route>
      </Routes>
    </main>
  );
}

export default App;
