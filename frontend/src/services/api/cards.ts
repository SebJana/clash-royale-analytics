import api from "./axios";
import type { Card, CardsResponse } from "../../types/cards";

export async function fetchAllCards(): Promise<Card[]> {
  const { data } = await api.get<CardsResponse>("/cards");
  return data.items;
}
