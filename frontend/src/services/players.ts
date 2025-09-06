import api from './axios';
import type { Players } from '../types/players'

export async function fetchAllTrackedPlayers(): Promise<Players> {
  const response = await api.get<Players>("/players");
  return response.data;
}