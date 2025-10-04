import { useQuery } from "@tanstack/react-query";
import { fetchDailyStats } from "../services/api/dailyStats";
import type { DailyStats } from "../types/dailyStats";

const min = 60_000;

export function useDailyStats(
  playerTag: string,
  startDate: string,
  endDate: string,
  gameModes?: string[] | null // Can be null to disable query until game modes are initialized
) {
  const modesKey = (gameModes ?? []).join("|"); // Make game modes a stable key

  return useQuery<DailyStats, Error>({
    queryKey: ["dailyStats", playerTag, startDate, endDate, modesKey],
    // Pass the playerTag to the query function from the query key
    queryFn: ({ queryKey }) => {
      const [, tag, start, end, modesString] = queryKey as [
        string,
        string,
        string,
        string,
        string
      ];
      const modes = modesString ? modesString.split("|") : undefined; // back to array from joined string
      return fetchDailyStats(tag, start, end, modes);
    },
    staleTime: 10 * min, // Cache duration, how long stats are considered fresh and aren't re-fetched from the backend
    gcTime: 15 * min,
    refetchOnWindowFocus: false,
    retry: false, // Don't retry to avoid long waits when no data is found
    enabled: gameModes !== null, // Only run query when gameModes are initialized (prevents double loading)
  });
}
