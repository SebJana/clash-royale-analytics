import { useQuery } from "@tanstack/react-query";
import { fetchDeckStats } from "../services/api/deckStats";
import type { DeckStats } from "../types/deckStats";

const min = 60_000;

export function useDeckStats(
  playerTag: string,
  startDate: string,
  endDate: string,
  gameModes?: string[]
) {
  const modesKey = (gameModes ?? []).join("|"); // Make game modes a stable key

  return useQuery<DeckStats, Error>({
    queryKey: ["deckStats", playerTag, startDate, endDate, modesKey],
    // Pass the playerTag to the query function from the query key
    queryFn: ({ queryKey }) => {
      const [, tag, start, end, modes] = queryKey;
      return fetchDeckStats(
        tag as string,
        start as string,
        end as string,
        modes as string[] | undefined
      );
    },
    staleTime: 10 * min, // Cache duration
    gcTime: 15 * min,
    refetchOnWindowFocus: false,
  });
}
