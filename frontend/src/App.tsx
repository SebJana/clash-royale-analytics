import { Routes, Route } from 'react-router-dom'
import HomePage from "./pages/home/home";
import PlayerHomePage from './pages/player/home/home';
import "./App.css";

function App() {

  return (
    <main className="main-container">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/player/:playerTag" element={<PlayerHomePage />} />
      </Routes>
    </main>
  );
}

export default App;
