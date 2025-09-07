import { Autocomplete, TextField, ListItem, ListItemText } from "@mui/material";

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
    <Autocomplete
      options={options}
      value={value}
      getOptionLabel={(option) => option.label}
      slotProps={{
        listbox: {
          style: { maxHeight: 240, overflow: "auto" },
        },
      }}
      renderOption={(props, option) => {
        const { key, ...optionProps } = props;
        return (
          <ListItem key={key} {...optionProps} disableGutters>
            <ListItemText
              primary={option.name}
              secondary={option.tag}
              slotProps={{
                primary: { noWrap: true },
                secondary: { noWrap: true },
              }}
            />
          </ListItem>
        );
      }}
      renderInput={(params) => (
        <TextField {...params} label="Search players…" size="small" />
      )}
      onChange={(_, selected) => {
        if (selected && onSelectPlayer) {
          onSelectPlayer(selected); // notify parent upon changed selection
        }
      }}
    />
  );
}
