import { useQuery } from "@tanstack/react-query";
import { fetchAllCards } from "../services/api/cards";
import type { Card } from "../types/cards";

const min = 60_000;

export function useCards() {
  return useQuery<Card[], Error>({
    queryKey: ["cards"],
    queryFn: fetchAllCards,
    staleTime: 15 * min, // Cache duration, how long cards are considered fresh and aren't re-fetched from the backend
    refetchOnWindowFocus: false,
  });
}