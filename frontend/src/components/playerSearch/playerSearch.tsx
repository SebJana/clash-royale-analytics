import { Autocomplete, TextField, ListItem, ListItemText } from "@mui/material";

type Player = { tag: string; name: string };

export function PlayerSearch({ players }: Readonly<{ players: Player[] }>) {
  const options = players.map((p) => ({
    ...p,
    label: `${p.name} (${p.tag})`, // combined key used for search/display
  }));

  // Search client-sided and fetch the complete dict of every tracked player for the client 
  // If tracked players count exceeds 1k+ the search should be moved and filtered 
  // server-sided using the indexed player collection in mongo
  return (
    <Autocomplete
      options={options}
      // Search uses `label`, which includes name + tag
      getOptionLabel={(option) => option.label}
      // Scrollable dropdown
      slotProps={{
        listbox: {
          style: { maxHeight: 240, overflow: "auto" }
        }
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
                secondary: { noWrap: true }
              }}
            />
          </ListItem>
        );
      }}
      renderInput={(params) => (
        <TextField {...params} label="Search players…" size="small" />
      )}
      onChange={(_, selected) => {
        if (selected) {
          console.log("Selected:", selected.tag, selected.name);
        }
      }}
    />
  );
}