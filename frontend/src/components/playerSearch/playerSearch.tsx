import { Autocomplete, TextField, ListItem, ListItemText } from "@mui/material";
import "./playerSearch.css";

type Player = { tag: string; name: string };

export function PlayerSearch({
  players,
  selectedPlayerTag,
  onSelectPlayer,
}: Readonly<{
  players: Player[];
  selectedPlayerTag?: string;
  onSelectPlayer?: (player: Player) => void;
}>) {
  const options = players.map((p) => ({
    ...p,
    label: `${p.name} (${p.tag})`, // combined key used for search/display
  }));

  const value = options.find((p) => p.tag === selectedPlayerTag) ?? null;

  // Search client-sided and fetch the complete dict of every tracked player for the client
  // If tracked players count exceeds 1k+ the search should be moved and filtered
  // server-sided using the indexed player collection in mongo

  // TODO show first N options of the current search, don't make it a scrollable list
  return (
    <div className="player-search">
      <Autocomplete
        options={options}
        value={value}
        getOptionLabel={(option) => option.label}
        renderOption={(props, option) => {
          const { key, ...optionProps } = props;
          return (
            <ListItem key={key} {...optionProps} disableGutters>
              <ListItemText primary={option.name} secondary={option.tag} />
            </ListItem>
          );
        }}
        renderInput={(params) => (
          <TextField {...params} label="Search players…" size="small" />
        )}
        onChange={(_, selected) => {
          if (selected && onSelectPlayer) {
            onSelectPlayer(selected);
          }
        }}
      />
    </div>
  );
}
