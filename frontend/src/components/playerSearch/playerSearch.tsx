import { createContext, useContext, useState } from "react";
import {
  Autocomplete,
  TextField,
  ListItem,
  ListItemText,
  Paper,
  type PaperProps,
} from "@mui/material";
import { ArrowRight } from "lucide-react";
import { usePlayerSearch } from "../../hooks/usePlayerSearch";
import type { PlayerSearchResult } from "../../types/players";
import { normalizePlayerTag } from "../../utils/playerTag";
import "./playerSearch.css";

type Player = { tag: string; name: string };
// A typed tag the search did not return. Offered as an option, so a player
// can be opened by tag even when search misses them or is unavailable.
type TypedTagOption = { tag: string; name: ""; match: "typedTag" };
type SearchOption = PlayerSearchResult | TypedTagOption;

// The dropdown paper reads this instead of taking a prop, so it can stay a
// stable component and MUI does not remount the list on every render.
const ShownCountContext = createContext<number | null>(null);

function playerLabel(player: Player): string {
  return player.name ? `${player.name} (${player.tag})` : player.tag;
}

function ResultsPaper({
  children,
  className,
  onMouseDown,
  ...props
}: PaperProps) {
  const shownCount = useContext(ShownCountContext);
  return (
    <Paper
      {...props}
      // MUI portals the dropdown out of .player-search; this class styles it.
      className={`${className ?? ""} player-search-paper`}
      // A click on the hint or padding keeps the input focused, so the list
      // stays open. Option clicks still select.
      onMouseDown={(event) => {
        event.preventDefault();
        onMouseDown?.(event);
      }}
    >
      {children}
      {shownCount !== null && (
        <div className="player-search-more-hint">
          Showing the first {shownCount} matches. Type more to narrow it down.
          Names aren't unique, only a tag (e.g. #YYRJQY28) is sure to find a
          specific account.
        </div>
      )}
    </Paper>
  );
}

// TODO Show the last 5-10 viewed players as options while the input is
// empty, so users can jump back without searching. Record a player when its
// page opens (pages/player/layout.tsx), newest first, without duplicates,
// and drop entries that come back PLAYER_NOT_TRACKED.
// Consent: keeping the list in localStorage on the device is likely exempt
// from consent under the "strictly necessary for a service the user asked
// for" rule (Art. 5(3) ePrivacy, § 25(2) Nr. 2 TDDDG), like the React Query
// cache and auth state already stored there. That holds only while the list
// never leaves the browser (not sent to the API, not used for analytics) and
// users can clear it, e.g. with a "Clear" action, plus a line in the privacy
// notice. A recently viewed list the user never turned on is a grey area, so
// an opt-in "Remember viewed players" toggle is the safe variant. Sending the
// list to the server or using it for statistics would need consent.
export function PlayerSearch({
  onSelectPlayer,
}: Readonly<{
  onSelectPlayer?: (player: Player | null) => void;
}>) {
  const [selected, setSelected] = useState<SearchOption | null>(null);
  // Only typed text is searched. Selecting a player fills the input with its
  // label, which is not a query.
  const [searchText, setSearchText] = useState("");
  const { data, isFetching, isError } = usePlayerSearch(searchText);

  const results = searchText.trim() ? (data?.players ?? []) : [];
  const shownCount = searchText.trim() && data?.hasMore ? results.length : null;

  const typedTag = normalizePlayerTag(searchText);
  let options: SearchOption[] = results;
  if (typedTag && !results.some((p) => p.tag === typedTag)) {
    const typed: TypedTagOption = {
      tag: typedTag,
      name: "",
      match: "typedTag",
    };
    // With "#" the tag is clearly meant; without, names stay on top.
    options = searchText.trim().startsWith("#")
      ? [typed, ...results]
      : [...results, typed];
  }
  // MUI expects the selected value among the options.
  if (selected && !options.some((p) => p.tag === selected.tag)) {
    options = [selected, ...options];
  }

  let noOptionsText = "No tracked players found";
  if (!searchText.trim()) noOptionsText = "Type a player name or tag";
  else if (isError)
    noOptionsText = "Search is unavailable right now. A full tag still works.";

  return (
    <div className="player-search">
      <ShownCountContext.Provider value={shownCount}>
        <Autocomplete
          options={options}
          value={selected}
          // The server already ranked and filtered the results.
          filterOptions={(x) => x}
          // Enter picks the first option, the best match.
          autoHighlight
          getOptionLabel={playerLabel}
          isOptionEqualToValue={(option, value) => option.tag === value.tag}
          loading={isFetching}
          noOptionsText={noOptionsText}
          slots={{ paper: ResultsPaper }}
          onInputChange={(_, value, reason) => {
            if (reason === "input" || reason === "clear") setSearchText(value);
          }}
          renderOption={(props, option) => {
            const { key, className, ...optionProps } = props;
            if (option.match === "typedTag") {
              // Styled as an action, not a result: it opens a page by tag
              // without the search having found the player.
              return (
                <ListItem
                  key={key}
                  {...optionProps}
                  className={`${className ?? ""} player-search-typed-tag`}
                  disableGutters
                >
                  <ListItemText
                    primary={
                      <span className="player-search-typed-tag-action">
                        Open {option.tag}
                        <ArrowRight aria-hidden="true" />
                      </span>
                    }
                    secondary="Not a search result, opens the player by tag"
                  />
                </ListItem>
              );
            }
            return (
              <ListItem
                key={key}
                {...optionProps}
                className={className}
                disableGutters
              >
                <ListItemText
                  primary={option.name || option.tag}
                  secondary={option.tag}
                />
              </ListItem>
            );
          }}
          renderInput={(params) => (
            <TextField {...params} label="Search players…" size="small" />
          )}
          onChange={(_, player) => {
            setSelected(player);
            onSelectPlayer?.(player);
          }}
        />
      </ShownCountContext.Provider>
    </div>
  );
}
