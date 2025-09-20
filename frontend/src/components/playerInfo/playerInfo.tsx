import type { Player } from "../../types/player";
import { round } from "../../utils/round";
import { StatCard } from "../statCard/StatCard";
import "./playerInfo.css";

/**
 * Get the account creation date given an account age in days.
 *
 * @param {number} accountAgeDays - Number of days since the account was created.
 * @returns {string} The calculated account creation date in YYYY-MM-DD format.
 */
function getAccountCreationDate(accountAgeDays: number): string {
  const today = new Date(); // current date & time
  const result = new Date(today); // copy
  result.setDate(result.getDate() - accountAgeDays);
  return result.toISOString().split("T")[0]; // keep only YYYY-MM-DD
}

/**
 * Get how many years, weeks, and days have passed since account creation.
 * Does not take leap years into account.
 *
 * @param {string} creationDateStr - Account creation date in YYYY-MM-DD format.
 * @returns {{ years: number, weeks: number, days: number }}
 *   Object with elapsed years, weeks, and days.
 */
function getAccountAgeBreakdown(creationDateStr: string) {
  const creationDate = new Date(creationDateStr);
  const today = new Date();

  // difference in total days
  const diffMs = today.getTime() - creationDate.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  // break down into years, weeks, and days
  const years = Math.floor(diffDays / 365);
  const remainingDaysAfterYears = diffDays % 365;

  const weeks = Math.floor(remainingDaysAfterYears / 7);
  const days = remainingDaysAfterYears % 7;

  return { years, weeks, days };
}

export function PlayerInfo({
  player,
}: Readonly<{
  player: Player;
}>) {
  const accountAgeDays =
    player?.badges?.find((b) => b.name === "YearsPlayed")?.progress ?? 0;

  const accountCreationDate = getAccountCreationDate(accountAgeDays);
  const elapsedTimeSplit = getAccountAgeBreakdown(accountCreationDate);

  const winPercentage =
    player?.battleCount > 0
      ? round((player?.wins / player?.battleCount) * 100, 1)
      : 0;

  return (
    <div className="player-info-component-container">
      <div className="player-info-component-header">
        <div className="player-info-component-basic-info">
          <h1 className="player-info-component-name">{player?.name}</h1>
          <p className="player-info-component-tag">{player?.tag}</p>
          {player?.clan?.name && (
            <p className="player-info-component-clan"> 🛡️ {player.clan.name}</p>
          )}
          {player?.arena?.name && (
            <p className="player-info-component-arena">
              🏟️ {player.arena.name}
            </p>
          )}
          {Boolean(player?.trophies) && (
            <p className="player-info-component-trophies">
              🏆 {player.trophies.toLocaleString()}
            </p>
          )}
        </div>
      </div>

      <div className="player-info-component-details">
        <div className="player-info-component-account-info-section">
          <h3>Account Information</h3>
          <div className="player-info-component-info-grid">
            <div className="player-info-component-info-item">
              <span className="player-info-component-info-label">
                Created On:
              </span>
              <span className="player-info-component-info-value">
                {accountCreationDate}
              </span>
            </div>
            <div className="player-info-component-info-item">
              <span className="player-info-component-info-label">
                Account Age:
              </span>
              <span className="player-info-component-info-value">
                {elapsedTimeSplit.years}y {elapsedTimeSplit.weeks}w{" "}
                {elapsedTimeSplit.days}d
              </span>
            </div>
          </div>
        </div>

        <div className="player-info-component-battle-stats-section">
          <h3>Battle Statistics</h3>
          <div className="player-info-component-stats-grid">
            <StatCard
              value={player?.wins?.toLocaleString() ?? 0}
              label="Wins"
            />
            <StatCard
              value={player?.losses?.toLocaleString() ?? 0}
              label="Losses"
            />
            <StatCard
              value={player?.battleCount?.toLocaleString() ?? 0}
              label="Total Battles"
            />
            <StatCard value={`${winPercentage}%`} label="Win Rate" />
            <StatCard
              value={player?.threeCrownWins.toLocaleString()}
              label="Three Crown Wins"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
