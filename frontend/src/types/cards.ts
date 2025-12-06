export type CardMeta = {
  name: string;
  id: number;
  maxLevel: number;
  maxEvolutionLevel?: number;
  elixirCost: number;
  iconUrls: {
    medium: string;
    evolutionMedium?: string;
    heroMedium?: string;
  };
  rarity: "common" | "rare" | "epic" | "legendary" | "champion";
};

export type CardsResponse = {
  items: CardMeta[];
};

export type Card = {
  name: string;
  id: number;
  level?: number;
  evolutionLevel?: number;
};
