// Only type YearsPlayed for display of account age
type Badge = {
  name: string;
  level: number;
  maxLevel: number;
  progress: number;
  target: number;
  // There is also iconUrls, but no display needed/planned
};

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
  badges?: Badge[];
};
