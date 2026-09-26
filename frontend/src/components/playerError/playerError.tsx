import { useState } from "react";
import { AlertCircle } from "lucide-react";
import "./playerError.css";

export type PlayerErrorSource = {
  label: string;
  failed: boolean;
  retry: () => Promise<unknown>;
};

export function PlayerError({
  sources,
  message,
}: Readonly<{
  sources: PlayerErrorSource[];
  message?: string;
}>) {
  const [isRetrying, setIsRetrying] = useState(false);
  const failedSources = sources.filter((source) => source.failed);
  const names = failedSources.map((source) => source.label);
  const sourceList =
    names.length > 1
      ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`
      : names[0];

  const retry = async () => {
    setIsRetrying(true);
    // Retry every failed request; one successful request should not hide another failure.
    await Promise.allSettled(failedSources.map((source) => source.retry()));
    setIsRetrying(false);
  };

  return (
    <section className="player-page-error" role="alert">
      <AlertCircle className="player-page-error-icon" aria-hidden="true" />
      <h2>Couldn't load this page</h2>
      <p>
        {message ??
          `Looks like the ${sourceList} went missing on the way here. Try again in a moment.`}
      </p>
      <div className="player-page-error-actions">
        <button
          type="button"
          onClick={() => void retry()}
          disabled={isRetrying}
        >
          {isRetrying ? "Trying again..." : "Try again"}
        </button>
      </div>
    </section>
  );
}
