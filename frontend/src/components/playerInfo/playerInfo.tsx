import type { Player } from "../../types/player";
import "./playerInfo.css";

export function PlayerInfo({
  player,
}: Readonly<{
  player: Player;
}>) {
  return (
    <>
      <h2>{player?.name}</h2>
      <h3>
        {" "}
        Account Age:{" "}
        {player?.badges?.find((b) => b.name === "YearsPlayed")?.progress ??
          "--"}
        {" Days"}
      </h3>
    </>
  );
}
