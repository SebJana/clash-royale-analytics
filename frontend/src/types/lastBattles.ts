export type Card = {
  name: string;
  id: number;
  level: number;
  evolutionLevel?: number;
};

export type Player = {
  tag: string;
  name: string;
  crowns: number;
  kingTowerHitPoints: number;
  princessTowersHitPoints: number[];
  cards: Card[];
  supportCards?: Card[];
  elixirLeaked: number;
};

export type Battle = {
  battleTime: string;
  arena: string;
  gameMode: string;
  team: Player[];
  opponent: Player[];
  gameResult: "Victory" | "Defeat" | "Draw" | string;
};

export type LastBattles = {
  player_tag: string;
  last_battles: {
    battles: Battle[];
    latestBattleTime: string;
    earliestBattleTime: string;
  };
};
