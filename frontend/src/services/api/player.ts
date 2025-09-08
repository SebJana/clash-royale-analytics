import api from "./axios";
import { validatePlayerTagSyntax } from "../../utils/playerTag";
import type { Player } from "../../types/player";

export async function fetchPlayerProfile(playerTag: string): Promise<Player> {
  // Throw error if an invalid player tag was passed
  if (!validatePlayerTagSyntax(playerTag)) {
    throw new Error("Invalid player tag");
  }

  const tag = encodeURIComponent(playerTag);
  const response = await api.get<Player>(`/players/${tag}/profile`);
  return response.data;
}
