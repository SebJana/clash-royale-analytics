import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent,
} from "react";
import { Button, CircularProgress } from "@mui/material";
import {
  Bot,
  Cherry,
  Citrus,
  Gauge,
  Grape,
  Heart,
  Pause,
  Play,
  RotateCcw,
  UserRound,
  Zap,
} from "lucide-react";
import { jwtDecode } from "jwt-decode";
import axios from "axios";
import {
  buzzHalliGalliRound,
  getHalliGalliCard,
  getHalliGalliGame,
  getHalliGalliStatus,
  nextHalliGalliRound,
  revealHalliGalliRound,
} from "../../services/api/auth";
import type {
  HalliGalliGameResponse,
  HalliGalliRoundReason,
  HalliGalliRoundResponse,
} from "../../types/auth";
import {
  calibrateHalliGalli,
  decryptHalliGalliCard,
  matchingCard,
  type EncryptedCard,
} from "./halliGalliProtocol";
import {
  addVisibleCard,
  afterRound,
  createSettlementGate,
  recoverSettledRound,
  scheduleNextCard,
  type VisibleCard,
} from "./halliGalliFlow";
import "./halliGalli.css";

type Phase =
  | "loading"
  | "ready"
  | "starting"
  | "playing"
  | "settling"
  | "advancing"
  | "animating"
  | "round_ready"
  | "won"
  | "lost"
  | "error";
const ROUND_FEEDBACK_MS = 2200;

const feedbackText: Record<HalliGalliRoundReason, string> = {
  correct_buzz: "Halli Galli! The bot loses a life.",
  late_buzz: "Too late!",
  wrong_card: "That was not the right card. You lost a life.",
  wrong_fruit: "That was not the target fruit. You lost a life.",
  false_buzz: "No Halli Galli yet. You lost a life.",
  missed_halli_galli: "The bot got there first. You lost a life.",
  no_halli_galli: "No Halli Galli. Next card!",
};

interface HalliGalliProps {
  readonly wordleToken: string;
  readonly onWin: (token: string) => void;
  readonly onWordleExpired: () => void;
}

/** Avoid opening a new connection for a token whose local expiry has passed. */
function tokenExpired(token: string): boolean {
  try {
    const { exp } = jwtDecode<{ exp?: number }>(token);
    return !exp || exp * 1000 <= Date.now();
  } catch {
    return true;
  }
}

/** Run one Halli Galli attempt inside the existing authentication modal. */
export function HalliGalli({
  wordleToken,
  onWin,
  onWordleExpired,
}: HalliGalliProps) {
  const [attempt, setAttempt] = useState(0);
  const [phase, setPhase] = useState<Phase>("loading");
  const [loadingStage, setLoadingStage] = useState<"calibrating" | "preparing">(
    "calibrating",
  );
  const [game, setGame] = useState<HalliGalliGameResponse | null>(null);
  const [pile, setPile] = useState<VisibleCard[]>([]);
  const [playerLives, setPlayerLives] = useState(0);
  const [botLives, setBotLives] = useState(0);
  const [progress, setProgress] = useState(0);
  const [feedback, setFeedback] = useState<HalliGalliRoundReason | null>(null);
  const [lateByMs, setLateByMs] = useState<number | null>(null);
  const [winningCardIds, setWinningCardIds] = useState<string[]>([]);
  const [clickedCardId, setClickedCardId] = useState<string | null>(null);
  const [winToken, setWinToken] = useState<string | null>(null);
  const [pauseAfterRound, setPauseAfterRound] = useState(false);
  const [gameEnded, setGameEnded] = useState(false);
  const [error, setError] = useState("");
  const pauseAfterRoundRef = useRef(false);
  const buzzRef = useRef<(card: VisibleCard, x: number, y: number) => void>(
    () => {},
  );
  const beginRef = useRef<() => void>(() => {});
  // Parent callbacks can change while the game is open. Read their latest
  // values without restarting calibration or discarding preloaded cards.
  const callbacksRef = useRef({ onWin, onWordleExpired });
  useEffect(() => {
    callbacksRef.current = { onWin, onWordleExpired };
  }, [onWin, onWordleExpired]);

  useEffect(() => {
    // This attempt owns its socket, timers, ciphertext, and object URLs. Effect
    // cleanup prevents a closed modal or old retry from updating the new game.
    let active = true;
    const controller = new AbortController();
    const ciphertext = new Map<number, EncryptedCard>();
    const pendingPreloads = new Map<number, Promise<void>>();
    const urls = new Set<string>();
    let visibleCards: VisibleCard[] = [];
    let timer: number | undefined;
    let barTimer: number | undefined;
    let feedbackTimer: number | undefined;
    let cancelNext = () => {};
    let currentRound = -1;
    let roundDue = 0;
    const settlementGate = createSettlementGate();
    let gameId = "";
    let gameData: HalliGalliGameResponse;

    /** The bar measures the next-card interval, never the hidden buzz deadline. */
    function progressAt(due: number) {
      return Math.max(
        0,
        Math.min(
          100,
          100 *
            (1 - (due - performance.now()) / gameData.next_card_interval_ms),
        ),
      );
    }
    /** Stop both the next action and the bar when a round or attempt ends. */
    function clearTimer() {
      cancelNext();
      window.clearTimeout(timer);
      window.clearInterval(barTimer);
      window.clearTimeout(feedbackTimer);
    }
    function clearVisiblePile() {
      const oldPile = visibleCards;
      visibleCards = afterRound(visibleCards, true);
      setPile(visibleCards);
      for (const old of oldPile) {
        urls.delete(old.url);
        window.setTimeout(() => URL.revokeObjectURL(old.url), 0);
      }
    }
    /** Separate an expired Wordle token from retryable game or network errors. */
    function fail(err: unknown) {
      if (!active) return;
      clearTimer();
      if (
        (axios.isAxiosError(err) && err.response?.status === 401) ||
        (err instanceof Error && err.message.includes("invalid_wordle_token"))
      ) {
        callbacksRef.current.onWordleExpired();
        return;
      }
      setPhase("error");
      if (axios.isAxiosError(err) && err.response?.status === 429) {
        setError("Too many requests. Wait a minute, then try again.");
      } else if (axios.isAxiosError(err) && err.response?.status === 404) {
        setError("This game expired. Start a new Halli Galli game.");
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "Halli Galli could not continue.",
        );
      }
    }
    /** Wait for the next-card cadence or result feedback to finish. */
    function waitUntil(when: number): Promise<void> {
      return new Promise((resolve) => {
        timer = window.setTimeout(
          resolve,
          Math.max(0, when - performance.now()),
        );
      });
    }
    /** Fetch one encrypted version per round; a second POST rotates its key. */
    async function preload(index: number, imageId: string) {
      if (ciphertext.has(index)) return;
      if (pendingPreloads.has(index)) return pendingPreloads.get(index);
      // Concurrent callers share this in-flight request instead of rotating the
      // key twice and leaving an old ciphertext beside a newer reveal key.
      const request = getHalliGalliCard(gameId, index)
        .then((result) => {
          if (active) ciphertext.set(index, { ...result, imageId });
        })
        .finally(() => pendingPreloads.delete(index));
      pendingPreloads.set(index, request);
      return request;
    }
    /** Reveal the matching preloaded image and start this round's UI clock. */
    async function reveal(index: number, imageId: string) {
      await preload(index, imageId);
      if (!active) return;
      let response;
      try {
        response = await revealHalliGalliRound(gameId, index);
      } catch (requestError) {
        // Reveal retries return the original key and deadline. Recover a lost
        // reply only while status still points at this same current round.
        const status = await getHalliGalliStatus(gameId);
        if (status.current_round !== index || status.game_status !== "playing")
          throw requestError;
        response = await revealHalliGalliRound(gameId, index);
      }
      // The server starts its clock on reveal. Start the next-card bar only
      // after decryption, when the card can actually be shown.
      const card = ciphertext.get(index);
      if (!card || !matchingCard(card, response)) {
        throw new Error("The preloaded card did not match its reveal version.");
      }
      const url = await decryptHalliGalliCard(card, response.encryption_key);
      if (!active) {
        URL.revokeObjectURL(url);
        return;
      }
      urls.add(url);
      window.clearTimeout(feedbackTimer);
      ciphertext.delete(index);
      currentRound = index;
      settlementGate.open(index);
      window.clearInterval(barTimer);
      // Revoke cards that fell outside the backend's visible-card window. The
      // timeout gives React a chance to remove their images from the screen.
      const nextPile = addVisibleCard(
        visibleCards,
        { roundIndex: index, imageId, url },
        gameData.rules.visible_card_count,
      );
      for (const old of visibleCards) {
        if (!nextPile.includes(old)) {
          urls.delete(old.url);
          window.setTimeout(() => URL.revokeObjectURL(old.url), 0);
        }
      }
      visibleCards = nextPile;
      setPile(nextPile);
      setFeedback(null);
      setLateByMs(null);
      setWinningCardIds([]);
      setClickedCardId(null);
      pauseAfterRoundRef.current = false;
      setPauseAfterRound(false);
      setGameEnded(false);
      roundDue = performance.now() + gameData.next_card_interval_ms;
      setPhase("playing");
      setProgress(0);
      barTimer = window.setInterval(() => {
        setProgress(progressAt(roundDue));
      }, 50);
      cancelNext = scheduleNextCard(roundDue, () => {
        void settle(index);
      });
    }
    /** Send one buzz or timed advance, then use saved status if its reply is lost. */
    async function settle(
      index: number,
      buzz?: { imageId: string; x: number; y: number },
    ) {
      if (!active || !settlementGate.claim(index)) return;
      // Freeze the bar at the buzz point and cancel the automatic action.
      // A timed advance has already reached the end of the bar.
      if (buzz) {
        cancelNext();
        window.clearInterval(barTimer);
        setProgress(progressAt(roundDue));
      } else {
        clearTimer();
        setProgress(100);
      }
      setPhase(buzz ? "settling" : "advancing");
      let result: HalliGalliRoundResponse;
      try {
        try {
          result = buzz
            ? await buzzHalliGalliRound(
                gameId,
                index,
                buzz.imageId,
                buzz.x,
                buzz.y,
              )
            : await nextHalliGalliRound(gameId, index);
        } catch (requestError) {
          // The request may have committed even if its response was lost. Read
          // status before considering another action for the same round.
          const status = await getHalliGalliStatus(gameId);
          if (
            status.current_round === index &&
            !buzz &&
            axios.isAxiosError(requestError) &&
            requestError.response?.status === 409
          ) {
            // Every round rejects an early next, including ordinary rounds.
            // Wait briefly instead of treating 409 as a clue about the cards.
            settlementGate.release(index);
            timer = window.setTimeout(() => {
              void settle(index);
            }, 150);
            return;
          }
          const recovered = recoverSettledRound(status, index);
          if (!recovered) throw requestError;
          result = recovered;
        }
        if (!active) return;
        setPlayerLives(result.player_lives);
        setBotLives(result.bot_lives);
        setFeedback(result.round_reason);
        setLateByMs(result.late_by_ms);
        setWinningCardIds(result.winning_card_ids);
        setClickedCardId(buzz?.imageId ?? null);
        setGameEnded(result.game_status !== "playing");
        const scored = result.round_result !== "no_halli_galli";
        const feedbackDue = performance.now() + ROUND_FEEDBACK_MS;
        if (scored) {
          // Keep the settled cards in place while their answer is highlighted.
          // Clear after feedback even if preparation takes longer or the
          // player has chosen to pause before the next reveal.
          setPhase("animating");
          feedbackTimer = window.setTimeout(() => {
            if (
              active &&
              result.clear_cards &&
              result.game_status === "playing"
            )
              clearVisiblePile();
          }, ROUND_FEEDBACK_MS);
        }
        if (result.game_status === "player_won") {
          if (result.halli_galli_token) {
            if (scored) await waitUntil(feedbackDue);
            if (!active) return;
            setWinToken(result.halli_galli_token);
            setPhase("won");
          } else throw new Error("The win token could not be recovered.");
          return;
        }
        if (result.game_status === "player_lost") {
          if (scored) await waitUntil(feedbackDue);
          if (!active) return;
          setPhase("lost");
          return;
        }
        const next = result.next_card;
        if (!next) throw new Error("The next card is missing.");
        // Status recovery names the far end too, so both paths refill once.
        const future = result.preloaded_card ? [result.preloaded_card] : [];
        if (scored) {
          // Keep the scored board visible for feedback while preparing the next
          // window, and preserve the minimum card cadence.
          await preload(next.round_index, next.image_id);
          for (const card of future) {
            if (card.round_index > next.round_index)
              await preload(card.round_index, card.image_id);
          }
          await waitUntil(Math.max(roundDue, feedbackDue));
          if (!active) return;
        }
        if (pauseAfterRoundRef.current) {
          // The pause request only takes effect after the current round has
          // settled, before the next card is revealed.
          if (!scored) {
            await preload(next.round_index, next.image_id);
            for (const card of future) {
              if (card.round_index > next.round_index)
                await preload(card.round_index, card.image_id);
            }
          }
          if (!active) return;
          let resumed = false;
          pauseAfterRoundRef.current = false;
          setPauseAfterRound(false);
          beginRef.current = () => {
            if (resumed || !active) return;
            resumed = true;
            window.clearTimeout(feedbackTimer);
            if (result.clear_cards) clearVisiblePile();
            setPhase("starting");
            void reveal(next.round_index, next.image_id).catch(fail);
          };
          setPhase("round_ready");
          return;
        }
        if (result.clear_cards) clearVisiblePile();
        if (active) await reveal(next.round_index, next.image_id);
        // On an ordinary round the next image is already cached. Reveal it
        // before fetching the far future image so the cadence stays smooth.
        if (!buzz) {
          for (const card of future) {
            if (card.round_index > next.round_index)
              await preload(card.round_index, card.image_id);
          }
        }
      } catch (err) {
        fail(err);
      }
    }
    buzzRef.current = (card, x, y) => {
      void settle(currentRound, { imageId: card.imageId, x, y });
    };

    /** Calibrate, create the game, and fill its initial window before play. */
    async function start() {
      try {
        if (tokenExpired(wordleToken)) {
          callbacksRef.current.onWordleExpired();
          return;
        }
        setPhase("loading");
        setLoadingStage("calibrating");
        setError("");
        setPile([]);
        setFeedback(null);
        setLateByMs(null);
        setWinningCardIds([]);
        setClickedCardId(null);
        pauseAfterRoundRef.current = false;
        setPauseAfterRound(false);
        setGameEnded(false);
        setWinToken(null);
        const calibrationId = await calibrateHalliGalli(
          wordleToken,
          controller.signal,
        );
        if (!active) return;
        setLoadingStage("preparing");
        gameData = await getHalliGalliGame(wordleToken, calibrationId);
        if (!active) return;
        gameId = gameData.halli_galli_id;
        setGame(gameData);
        setPlayerLives(gameData.player_lives);
        setBotLives(gameData.bot_lives);
        // Fetch serially because every preload updates the same Redis game.
        for (const card of gameData.initial_cards) {
          await preload(card.round_index, card.image_id);
        }
        if (!active) return;
        const first = gameData.initial_cards.find(
          (card) => card.round_index === gameData.current_round,
        );
        if (!first) throw new Error("The first card is missing.");
        // Hold the first reveal until the player has read this game's rules.
        // The server's reaction clock starts only when reveal is requested.
        let started = false;
        beginRef.current = () => {
          if (started || !active) return;
          started = true;
          setPhase("starting");
          void reveal(first.round_index, first.image_id).catch(fail);
        };
        setPhase("ready");
      } catch (err) {
        fail(err);
      }
    }
    void start();
    return () => {
      active = false;
      beginRef.current = () => {};
      controller.abort();
      clearTimer();
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [attempt, wordleToken]);

  function handleCardClick(
    event: MouseEvent<HTMLButtonElement>,
    card: VisibleCard,
  ) {
    if (phase !== "playing") return;
    const image = event.currentTarget.querySelector("img");
    if (!image) return;
    const rect = image.getBoundingClientRect();
    // The image fills its own button without cropping, so this point matches
    // the server's normalized PNG coordinates on mouse and touch screens.
    const x = Math.max(
      0,
      Math.min(1, (event.clientX - rect.left) / rect.width),
    );
    const y = Math.max(
      0,
      Math.min(1, (event.clientY - rect.top) / rect.height),
    );
    buzzRef.current(card, x, y);
  }

  const visibleCount = game?.rules.visible_card_count ?? 1;
  const desktopRows = Math.ceil(visibleCount / 4);
  const mobileRows = Math.ceil(visibleCount / 2);
  const messageTone =
    phase === "won" || (phase === "animating" && feedback === "correct_buzz")
      ? "good"
      : phase === "lost" ||
          (phase === "animating" && feedback && feedback !== "no_halli_galli")
        ? "bad"
        : "neutral";
  const showingResultCards =
    phase === "animating" ||
    phase === "round_ready" ||
    phase === "won" ||
    phase === "lost";
  const timerIdle =
    phase === "ready" ||
    phase === "starting" ||
    phase === "round_ready" ||
    phase === "won" ||
    phase === "lost" ||
    phase === "error";
  const pauseLabel = pauseAfterRound
    ? "Cancel scheduled pause"
    : "Pause after this round";
  const feedbackMessage = feedback ? feedbackText[feedback] : null;
  const lateBuzzDetail =
    feedback === "late_buzz"
      ? `${lateByMs === null ? "Your buzz missed the deadline." : `${lateByMs} ms past the deadline.`} ${gameEnded ? "That was your last life." : "You lost a life."}`
      : null;
  const lateBuzzIcon =
    feedback === "late_buzz" ? (
      <Gauge className="halli-late-icon" size={38} aria-hidden="true" />
    ) : null;
  const ruleText = game && (
    <>
      <p>
        Buzz when one fruit totals exactly{" "}
        <strong>{game.rules.winning_fruit_count}</strong> across the visible
        cards. Every visible card counts, including all{" "}
        <strong>{game.rules.visible_card_count}</strong> once they are shown.
      </p>
      <p>
        Count only the <strong>actual fruit emojis</strong>. Ignore colored
        blobs, noise, and all other distractions.
      </p>
      <p className="halli-click-rule">
        Click the <strong>{game.rules.winning_card_age}</strong> card of the{" "}
        <strong>winning fruit</strong>.{" "}
        {game.rules.require_target_fruit ? (
          <>
            Click the <strong>{game.rules.target_fruit_edge}most</strong> fruit
            on that card.
          </>
        ) : (
          <>
            Click <strong>anywhere</strong> on that card.
          </>
        )}
      </p>
      <p>
        Be quicker than the bot: a correct buzz costs it one life. If it gets
        there first, you lose one. An incorrect buzz also costs you one life.
        The bar is a guide to the next card; the bot can beat you before it
        fills.
      </p>
    </>
  );

  return (
    <div className={`halli-galli auth-step phase-${phase}`}>
      <h3 className="auth-stage-heading">
        Play Halli Galli to prove your reaction speed
      </h3>
      {phase === "loading" && (
        <div className={`halli-loading is-${loadingStage}`} role="status">
          <div className={`halli-loading-visual is-${loadingStage}`}>
            {loadingStage === "calibrating" && (
              <div className="halli-loading-fruits" aria-hidden="true">
                <Cherry size={30} />
                <Citrus size={30} />
                <Grape size={30} />
              </div>
            )}
            <span className="halli-loading-core">
              <CircularProgress
                className="halli-loading-spinner"
                size={40}
                aria-label="Loading Halli Galli"
              />
            </span>
          </div>
          <div className="halli-loading-copy">
            <strong>
              {loadingStage === "calibrating"
                ? "Checking connectivity…"
                : "Preparing cards…"}
            </strong>
          </div>
          <div className="halli-loading-dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </div>
      )}
      {game && phase !== "loading" && phase !== "error" && (
        <>
          <div className="halli-rules">{ruleText}</div>
          <details className="halli-mobile-rules">
            <summary>
              Buzz at {game.rules.winning_fruit_count} ·{" "}
              {game.rules.winning_card_age} winning card ·{" "}
              {game.rules.require_target_fruit
                ? `${game.rules.target_fruit_edge}most fruit`
                : "anywhere"}
            </summary>
            <div className="halli-rules">{ruleText}</div>
          </details>
          <div className="halli-lives" aria-label="Remaining lives">
            <div>
              <span>
                <UserRound size={18} /> You
              </span>
              <span aria-label={`${playerLives} lives left`}>
                {Array.from({ length: game.player_lives }, (_, i) => (
                  <Heart
                    key={i}
                    size={21}
                    fill={i < playerLives ? "currentColor" : "none"}
                    className={i < playerLives ? "life-active" : "life-empty"}
                  />
                ))}
              </span>
            </div>
            <div>
              <span>
                <Bot size={18} /> Bot
              </span>
              <span aria-label={`${botLives} lives left`}>
                {Array.from({ length: game.bot_lives }, (_, i) => (
                  <Heart
                    key={i}
                    size={21}
                    fill={i < botLives ? "currentColor" : "none"}
                    className={i < botLives ? "life-active" : "life-empty"}
                  />
                ))}
              </span>
            </div>
          </div>
          <div className="halli-timer-row">
            <span
              className={`halli-timer-label ${timerIdle ? "is-idle" : ""}`}
              aria-hidden={timerIdle}
            >
              Next card
            </span>
            <progress
              className={`halli-progress ${timerIdle ? "is-idle" : ""}`}
              aria-label="Next card interval"
              value={Math.round(progress)}
              max={100}
            />
            <div className="halli-pause-slot">
              {(phase === "playing" ||
                phase === "settling" ||
                phase === "advancing" ||
                (phase === "animating" && !gameEnded)) && (
                <Button
                  className="halli-pause-button"
                  variant={pauseAfterRound ? "contained" : "outlined"}
                  aria-label={pauseLabel}
                  title={pauseLabel}
                  aria-pressed={pauseAfterRound}
                  onClick={() => {
                    pauseAfterRoundRef.current = !pauseAfterRoundRef.current;
                    setPauseAfterRound(pauseAfterRoundRef.current);
                  }}
                >
                  {pauseAfterRound ? (
                    <Play size={20} fill="currentColor" aria-hidden="true" />
                  ) : (
                    <Pause size={20} fill="currentColor" aria-hidden="true" />
                  )}
                </Button>
              )}
            </div>
          </div>
          <div
            className="halli-pile"
            style={
              {
                "--visible-cards": Math.min(visibleCount, 4),
                "--visible-cards-mobile": Math.min(visibleCount, 2),
                "--pile-rows-desktop": desktopRows,
                "--pile-rows-mobile": mobileRows,
                "--pile-height-desktop": `${desktopRows * 286 + (desktopRows - 1) * 8}px`,
              } as CSSProperties
            }
            // TODO keep sliding window for cards or have the n + 1 card replace the oldest
            // current card so that all cards keep their position until they're replaced
          >
            {phase === "animating" && (
              <div
                className={`halli-result-message ${messageTone} ${feedback === "correct_buzz" ? "is-correct" : ""} ${feedback === "missed_halli_galli" ? "is-missed" : ""}`}
                role="status"
              >
                {(feedback === "correct_buzz" ||
                  feedback === "missed_halli_galli") && (
                  <span className="halli-result-impact" aria-hidden="true">
                    <span className="halli-impact-ring" />
                    <span className="halli-impact-rays" />
                    {feedback === "correct_buzz" ? (
                      <Zap size={24} fill="currentColor" />
                    ) : (
                      <Bot size={24} />
                    )}
                  </span>
                )}
                {lateBuzzIcon}
                <strong>{feedbackMessage}</strong>
                {lateBuzzDetail && <span>{lateBuzzDetail}</span>}
              </div>
            )}
            {pile.map((card) => (
              <button
                type="button"
                key={card.roundIndex}
                className={[
                  "halli-card",
                  showingResultCards && winningCardIds.includes(card.imageId)
                    ? feedback === "correct_buzz"
                      ? "is-winning player-win"
                      : feedback === "missed_halli_galli"
                        ? "is-winning bot-win bot-steal"
                        : "is-winning bot-win"
                    : "",
                  showingResultCards &&
                  clickedCardId === card.imageId &&
                  (feedback === "wrong_card" || feedback === "false_buzz")
                    ? "is-wrong"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                disabled={phase !== "playing"}
                onClick={(event) => handleCardClick(event, card)}
                aria-label={`Card ${card.roundIndex + 1}; ${game.rules.require_target_fruit ? "click a fruit" : "click the card"} to buzz`}
              >
                <img
                  src={card.url}
                  alt={`Fruit card ${card.roundIndex + 1}`}
                  draggable={false}
                />
              </button>
            ))}
            {(phase === "starting" ||
              phase === "settling" ||
              phase === "advancing") && (
              <div
                className="halli-checking-status"
                role="status"
                aria-label={
                  phase === "settling"
                    ? "Checking your buzz"
                    : "Preparing the next card"
                }
              >
                <CircularProgress
                  size={22}
                  className="halli-spinner"
                  aria-hidden="true"
                />
              </div>
            )}
            {(phase === "ready" ||
              phase === "round_ready" ||
              phase === "won" ||
              phase === "lost") && (
              <div
                className={`halli-center-message phase-${phase} ${messageTone}`}
                role="status"
              >
                {phase === "ready" && (
                  <>
                    <h4>Ready to play?</h4>
                    <Button
                      variant="contained"
                      size="large"
                      className="auth-outcome-button is-success"
                      aria-label="Start game"
                      onClick={() => beginRef.current()}
                    >
                      <Play size={24} fill="currentColor" aria-hidden="true" />
                    </Button>
                  </>
                )}
                {phase === "round_ready" && (
                  <>
                    <h4>Paused</h4>
                    <Button
                      variant="contained"
                      size="large"
                      aria-label="Resume game"
                      title="Resume game"
                      onClick={() => beginRef.current()}
                    >
                      <Play size={24} fill="currentColor" aria-hidden="true" />
                    </Button>
                  </>
                )}
                {phase === "won" && (
                  <>
                    <h4>You won!</h4>
                    <p>You beat the bot.</p>
                    <Button
                      variant="contained"
                      size="large"
                      onClick={() => {
                        if (winToken) callbacksRef.current.onWin(winToken);
                      }}
                    >
                      Continue
                    </Button>
                  </>
                )}
                {phase === "lost" && (
                  <>
                    {lateBuzzIcon}
                    <h4>Game over</h4>
                    <p>{lateBuzzDetail ?? feedbackMessage}</p>
                    <Button
                      variant="contained"
                      size="large"
                      className="auth-outcome-button is-retry"
                      onClick={() => setAttempt((value) => value + 1)}
                    >
                      <RotateCcw size={18} aria-hidden="true" />
                      <span>Try Again</span>
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        </>
      )}
      {phase === "error" && (
        <div className="halli-finale bad" role="alert">
          <p>{error}</p>
          <Button
            variant="contained"
            className="auth-outcome-button is-retry"
            onClick={() => setAttempt((value) => value + 1)}
          >
            <RotateCcw size={18} aria-hidden="true" />
            <span>Try Again</span>
          </Button>
        </div>
      )}
    </div>
  );
}
