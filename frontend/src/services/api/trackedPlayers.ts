import api from "./axios";
import { validatePlayerTagSyntax } from "../../utils/playerTag";
import type { PlayerCount, PlayerSearchResponse } from "../../types/players";

/**
 * Search tracked players by name or tag, best match first.
 *
 * @param query - Text as typed. A leading "#" ranks tag matches first.
 * @param signal - Aborts the request once a newer query replaces it
 * @returns Up to SEARCH_RESULT_LIMIT ranked players (an API setting), and
 *   whether more players match
 */
export async function searchTrackedPlayers(
  query: string,
  signal?: AbortSignal,
): Promise<PlayerSearchResponse> {
  const response = await api.get<PlayerSearchResponse>("/players/search", {
    params: { q: query },
    signal,
  });
  return response.data;
}

export async function fetchAllTrackedPlayersCount(): Promise<PlayerCount> {
  const response = await api.get<PlayerCount>("/players/count");
  return response.data;
}

export async function trackPlayer(
  playerTag: string,
): Promise<{ status: string; tag: string }> {
  const tag = playerTag.trim();
  if (!validatePlayerTagSyntax(tag)) {
    throw new Error("Invalid player tag. Enter a tag like #YYRJQY28.");
  }

  const response = await api.post(`/players/${encodeURIComponent(tag)}`);
  return response.data;
}

export async function untrackPlayer(
  playerTag: string,
): Promise<{ status: string; tag: string }> {
  const tag = playerTag.trim();
  if (!validatePlayerTagSyntax(tag)) {
    throw new Error("Invalid player tag. Enter a tag like #YYRJQY28.");
  }

  const response = await api.delete(`/players/${encodeURIComponent(tag)}`);
  return response.data;
}
