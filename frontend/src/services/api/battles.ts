import api from "./axios";
import type { TotalBattleCount } from "../../types/battles";

export async function fetchTotalBattleCount(): Promise<TotalBattleCount> {
  const response = await api.get<TotalBattleCount>("/battles/total_count");
  return response.data;
}
