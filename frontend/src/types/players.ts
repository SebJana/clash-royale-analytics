export type PlayerCount = {
  activePlayerCount: number;
};

// NOTE: Keep in sync with MATCH_TYPES in backend/app/src/player_search/index.py.
export type PlayerSearchMatch =
  | "exactTag"
  | "exactName"
  | "namePrefix"
  | "nameWord"
  | "nameInfix"
  | "tagPrefix"
  | "tagInfix";

export type PlayerSearchResult = {
  tag: string;
  name: string;
  match: PlayerSearchMatch;
};

export type PlayerSearchResponse = {
  // Best match first
  players: PlayerSearchResult[];
  // More players match than were returned
  hasMore: boolean;
};
