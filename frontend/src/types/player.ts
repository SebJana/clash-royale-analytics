export type Player = {
  tag: string;
  name: string;
  trophies: number;
  wins: number;
  losses: number;
  battleCount: number;
  threeCrownWins: number;
  clan?: {
    name: string;
  };
  arena?: {
    name: string;
  };
};
