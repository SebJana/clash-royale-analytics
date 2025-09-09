import api from "./axios";
import type { CardMeta, CardsResponse } from "../../types/cards";

export async function fetchAllCards(): Promise<CardMeta[]> {
  const { data } = await api.get<CardsResponse>("/cards");
  return data.items;
}
