import { useInfiniteQuery } from "@tanstack/react-query";
import type { LastBattles } from "../types/lastBattles";
import { validatePlayerTagSyntax } from "../utils/playerTag";
import { fetchLastBattles } from "../services/api/lastBattles";

const min = 60_000;

export function usePlayerBattlesInfinite(
  playerTag: string,
  limit = 10,
  enabled = true
) {
  return useInfiniteQuery<LastBattles, Error>({
    queryKey: ["playerBattles", playerTag, limit],
    enabled: enabled && !!playerTag && validatePlayerTagSyntax(playerTag), // Check if given tag is valid
    initialPageParam: undefined as string | undefined, // first battles have no before time
    queryFn: ({ pageParam }) =>
      fetchLastBattles(playerTag, pageParam as string | undefined, limit),
    getNextPageParam: (lastPage) => {
      const lastBattle = lastPage.last_battles;
      const nextBefore = lastBattle.earliestBattleTime; // use earliest for "before"
      // Stop if no battles returned
      if (!lastBattle?.battles?.length) return undefined;
      // If earliestBattleTime is present, fetch older page using it
      return nextBefore || undefined;
    },
    staleTime: 5 * min,
    gcTime: 15 * min,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: 2, // Limit retries
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff for every retry
  });
}
