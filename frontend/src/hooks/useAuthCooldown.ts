import { useLayoutEffect, useState } from "react";
import type { AuthErrorFeedback } from "../utils/authErrors";

export function useAuthCooldown(feedback: AuthErrorFeedback | null) {
  const retryAt = feedback?.retryAt;
  const [remainingSeconds, setRemainingSeconds] = useState(0);

  // Set the wait before paint so a rate-limited button doesn't briefly look clickable.
  useLayoutEffect(() => {
    if (retryAt === undefined) {
      setRemainingSeconds(0);
      return;
    }
    // NOTE use the actual deadline, not a counter that loses time when the tab sleeps.
    // Round up so the button isn't enabled during the last fraction of a second.
    const secondsLeft = () =>
      Math.max(0, Math.ceil((retryAt - Date.now()) / 1000));
    setRemainingSeconds(secondsLeft());
    if (secondsLeft() === 0) return;

    const update = () => {
      const seconds = secondsLeft();
      setRemainingSeconds(seconds);
      if (seconds === 0) window.clearInterval(interval);
    };
    // Check more often than the displayed seconds, and catch up when returning to the tab.
    const interval = window.setInterval(update, 250);
    window.addEventListener("focus", update);
    document.addEventListener("visibilitychange", update);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("focus", update);
      document.removeEventListener("visibilitychange", update);
    };
  }, [retryAt]);

  // Reaching zero only unlocks the controls. The user still decides when to retry.
  const waitMessage =
    retryAt === undefined
      ? ""
      : remainingSeconds > 0
        ? ` Try again in ${remainingSeconds} second${remainingSeconds === 1 ? "" : "s"}.`
        : " You can try again now.";

  return {
    remainingSeconds,
    message: feedback ? feedback.message + waitMessage : "",
  };
}
