import { useQuery } from "@tanstack/react-query";
import { fetchAllCards } from "../services/api/cards";
import type { Card } from "../types/cards";

const minute = 60_000;

export function useCards() {
  return useQuery<Card[], Error>({
    queryKey: ["cards"],       // cache key
    queryFn: fetchAllCards,    // how to fetch
    staleTime: 1 * minute,     // 1 min fresh
    gcTime: 5 * minute,        // 5 min in cache
    refetchOnWindowFocus: false,
  });
}