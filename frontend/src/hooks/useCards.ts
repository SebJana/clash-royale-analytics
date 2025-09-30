import { useQuery } from "@tanstack/react-query";
import { fetchAllCards } from "../services/api/cards";
import type { CardMeta } from "../types/cards";

const min = 60_000;

// TODO pull cache times into settings file
export function useCards() {
  return useQuery<CardMeta[], Error>({
    queryKey: ["cards"],
    queryFn: fetchAllCards,
    staleTime: 15 * min, // Cache duration, how long cards are considered fresh and aren't re-fetched from the backend
    gcTime: 30 * min,
    refetchOnWindowFocus: false,
  });
}
