import api from "./axios";
import { validatePlayerTagSyntax } from "../../utils/playerTag";
import type { Players } from "../../types/players";

export async function fetchAllTrackedPlayers(): Promise<Players> {
  const response = await api.get<Players>("/players");
  return response.data;
}

export async function trackPlayer(
  playerTag: string
): Promise<{ status: string; tag: string }> {
  if (!validatePlayerTagSyntax(playerTag)) {
    throw new Error(`Player with tag ${playerTag} does not exist`);
  }

  const tag = encodeURIComponent(playerTag);
  const response = await api.post(`/players/${tag}`);
  return response.data;
}
