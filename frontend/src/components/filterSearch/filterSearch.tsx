import { Search } from "lucide-react";
import "./filterSearch.css";

export function FilterSearch({
  value,
  onChange,
  placeholder,
}: Readonly<{
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}>) {
  return (
    <label className="filter-search">
      <Search aria-hidden="true" />
      <input
        type="search"
        aria-label={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}
