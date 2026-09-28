import { PlayerError } from "../playerError/playerError";
import "./playerInfo.css";

export function PlayerInfoPlaceholder({
  tag,
  name,
  retry,
  retryAttempts,
  onRetryAttempt,
}: Readonly<{
  tag: string;
  name?: string;
  retry: () => Promise<unknown>;
  retryAttempts: number;
  onRetryAttempt: () => void;
}>) {
  return (
    <div className="player-info-component-container player-info-placeholder">
      <div className="player-info-component-basic-info">
        <h1 className="player-info-component-name">{name || "Player"}</h1>
        <p className="player-info-component-tag">{tag}</p>
      </div>
      <PlayerError
        compact
        title="Couldn't load player information"
        sources={[{ label: "player information", failed: true, retry }]}
        retryAttempts={retryAttempts}
        onRetryAttempt={onRetryAttempt}
      />
    </div>
  );
}
