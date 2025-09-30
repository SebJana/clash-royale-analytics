import type { Card } from "./cards";

export type CardStats = {
  player_tag: string;
  game_modes: string[] | null; // Applied filters on game mode
  card_statistics: {
    totalBattles: number;
    cards: Cards[];
  };
};

type Cards = {
  usage: number;
  wins: number;
  card: Card;
  winRate: number;
};
