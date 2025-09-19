import api from "./axios";
import type { GameModes } from "../../types/gameModes";

export async function fetchGameModes(): Promise<GameModes> {
  const response = await api.get<GameModes>("/game_modes");
  return response.data;
}
