import api from "./axios";
import { validatePlayerTagSyntax } from "../../utils/playerTag";
import type { Players, PlayerCount } from "../../types/players";

export async function fetchAllTrackedPlayers(): Promise<Players> {
  const response = await api.get<Players>("/players");
  return response.data;
}

export async function fetchAllTrackedPlayersCount(): Promise<PlayerCount> {
  const response = await api.get<PlayerCount>("/players/count");
  return response.data;
}

export async function trackPlayer(
  playerTag: string
): Promise<{ status: string; tag: string }> {
  const tag = playerTag.trim();
  if (!validatePlayerTagSyntax(tag)) {
    throw new Error("Invalid player tag. Enter a tag like #YYRJQY28.");
  }

  const response = await api.post(`/players/${encodeURIComponent(tag)}`);
  return response.data;
}

export async function untrackPlayer(
  playerTag: string
): Promise<{ status: string; tag: string }> {
  const tag = playerTag.trim();
  if (!validatePlayerTagSyntax(tag)) {
    throw new Error("Invalid player tag. Enter a tag like #YYRJQY28.");
  }

  const response = await api.delete(`/players/${encodeURIComponent(tag)}`);
  return response.data;
}
