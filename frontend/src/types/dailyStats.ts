export type DailyStats = {
  player_tag: string;
  game_modes: string[] | null; // Applied filters on game mode
  daily_statistics: {
    totalBattles: number;
    daily: Days[];
  };
};

type Days = {
  date: string;
  battles: number;
  victories: number;
  defeats: number;
  draws: number;
  crownsFor: number;
  crownsAgainst: number;
  elixirLeaked: number; // Summed leaked elixir
  winRate: number;
};
