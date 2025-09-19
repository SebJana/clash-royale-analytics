import type { Card } from "./cards";

export type DeckStats = {
  player_tag: string;
  game_modes: string[] | null; // Applied filters on game mode
  deck_statistics: {
    totalBattles: number;
    decks: Deck[];
  };
};

type Deck = {
  count: number;
  wins: number;
  firstSeen: string;
  lastSeen: string;
  modes: string[]; // Game modes in which the deck appeared
  deck: Card[];
};
