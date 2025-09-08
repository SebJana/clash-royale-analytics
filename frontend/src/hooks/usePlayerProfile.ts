import { useQuery } from "@tanstack/react-query";
import { fetchPlayerProfile } from "../services/api/player";
import type { Player } from "../types/player";

const min = 60_000;

export function usePlayerProfile(playerTag: string) {
  return useQuery<Player, Error>({
    queryKey: ["playerProfile", playerTag],
    // Pass the playerTag to the query function from the query key
    queryFn: ({ queryKey }) => {
      const [, tag] = queryKey;
      return fetchPlayerProfile(tag as string);
    },
    staleTime: 15 * min, // Cache duration, how long cards are considered fresh and aren't re-fetched from the backend
    refetchOnWindowFocus: false,
  });
}
