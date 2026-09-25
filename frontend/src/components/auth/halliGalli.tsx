import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent,
} from "react";
import { Button, CircularProgress } from "@mui/material";
import { Heart, Bot, Gauge, Play, UserRound, Wifi } from "lucide-react";
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
  needsManualStart,
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
  const [loadingText, setLoadingText] = useState("Testing your connection…");
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
  const [error, setError] = useState("");
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
    /** Keep the chosen card cadence and allow feedback to remain visible. */
    function pauseUntil(when: number): Promise<void> {
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
      // The server starts its clock on reveal; the public bar starts when its
      // response arrives and represents only the next-card interval.
      roundDue = performance.now() + gameData.next_card_interval_ms;
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
      setPhase("playing");
      setProgress(0);
      barTimer = window.setInterval(() => {
        setProgress(
          Math.min(
            100,
            100 *
              (1 -
                (roundDue - performance.now()) /
                  gameData.next_card_interval_ms),
          ),
        );
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
      // A buzz ends reaction time, while its bar keeps moving to the scheduled
      // next-card reveal. The automatic next action stops both timers.
      if (buzz) cancelNext();
      else clearTimer();
      if (!buzz) setProgress(100);
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
        const scored = result.round_result !== "no_halli_galli";
        if (scored) {
          // Keep the settled cards in place while their answer is highlighted.
          // Clearing on this timer also works when preparation takes longer
          // than the animation or the player waits at the Start button.
          setPhase("animating");
          feedbackTimer = window.setTimeout(() => {
            if (active && result.clear_cards) clearVisiblePile();
          }, ROUND_FEEDBACK_MS);
        }
        if (result.game_status === "player_won") {
          if (result.halli_galli_token) {
            window.clearInterval(barTimer);
            setWinToken(result.halli_galli_token);
            setPhase("won");
          } else throw new Error("The win token could not be recovered.");
          return;
        }
        if (result.game_status === "player_lost") {
          window.clearInterval(barTimer);
          setPhase("lost");
          return;
        }
        const next = result.next_card;
        if (!next) throw new Error("The next card is missing.");
        // Status recovery names the far end too, so both paths refill once.
        const future = result.preloaded_card ? [result.preloaded_card] : [];
        if (needsManualStart(result)) {
          // A scored round pauses on its result. Prepare the entire next window
          // before offering Start, but keep the original minimum card cadence.
          await preload(next.round_index, next.image_id);
          for (const card of future) {
            if (card.round_index > next.round_index)
              await preload(card.round_index, card.image_id);
          }
          await pauseUntil(roundDue);
          if (!active) return;
          window.clearInterval(barTimer);
          setProgress(100);
          let started = false;
          beginRef.current = () => {
            if (started || !active) return;
            started = true;
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
        setLoadingText("Testing your connection…");
        setError("");
        setPile([]);
        setFeedback(null);
        setLateByMs(null);
        setWinningCardIds([]);
        setClickedCardId(null);
        setWinToken(null);
        const calibrationId = await calibrateHalliGalli(
          wordleToken,
          controller.signal,
        );
        if (!active) return;
        setLoadingText("Preparing the cards…");
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
    feedback === "correct_buzz" || phase === "won"
      ? "good"
      : phase === "lost" || (feedback && feedback !== "no_halli_galli")
        ? "bad"
        : "neutral";
  const showingResultCards =
    phase === "animating" ||
    phase === "round_ready" ||
    phase === "won" ||
    phase === "lost";
  const feedbackMessage = feedback ? feedbackText[feedback] : null;
  const lateBuzzDetail =
    feedback === "late_buzz"
      ? `${lateByMs === null ? "Your buzz missed the deadline." : `${lateByMs} ms past the deadline.`} ${phase === "lost" ? "That was your last life." : "You lost a life."}`
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
      </p>
    </>
  );

  return (
    <div className={`halli-galli auth-step phase-${phase}`}>
      <h3>Play Halli Galli to prove your reaction speed</h3>
      {phase === "loading" && (
        <div className="halli-loading" role="status">
          <Wifi />
          <CircularProgress />
          <p>{loadingText}</p>
        </div>
      )}
      {game && phase !== "loading" && (
        <>
          <div className="halli-rules">{ruleText}</div>
          <details className="halli-mobile-rules">
            <summary>
              Buzz at {game.rules.winning_fruit_count} ·{" "}
              {game.rules.winning_card_age} winning card{" "}
              ·{" "}
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
          <progress
            className={`halli-progress ${phase === "ready" || phase === "starting" ? "is-idle" : ""}`}
            aria-label="Time until next card"
            value={Math.round(progress)}
            max={100}
          />
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
            {pile.map((card) => (
              <button
                type="button"
                key={card.roundIndex}
                className={[
                  "halli-card",
                  showingResultCards && winningCardIds.includes(card.imageId)
                    ? feedback === "correct_buzz"
                      ? "is-winning player-win"
                      : "is-winning bot-win"
                    : "",
                  showingResultCards &&
                  clickedCardId === card.imageId &&
                  feedback !== "correct_buzz"
                    ? "is-wrong"
                    : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                disabled={phase !== "playing"}
                onClick={(event) => handleCardClick(event, card)}
                aria-label={`Card ${card.roundIndex + 1}; click a fruit to buzz`}
              >
                <img
                  src={card.url}
                  alt={`Fruit card ${card.roundIndex + 1}`}
                  draggable={false}
                />
              </button>
            ))}
            {(phase === "ready" ||
              phase === "starting" ||
              phase === "settling" ||
              phase === "animating" ||
              phase === "round_ready" ||
              phase === "won" ||
              phase === "lost") && (
              <div
                className={`halli-center-message ${messageTone}`}
                role="status"
              >
                {phase === "ready" && (
                  <>
                    <h4>Ready to play?</h4>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<Play size={20} fill="currentColor" />}
                      onClick={() => beginRef.current()}
                    >
                      Start game
                    </Button>
                  </>
                )}
                {phase === "starting" && (
                  <>
                    <CircularProgress aria-label="Revealing card" />
                    <p>Revealing card…</p>
                  </>
                )}
                {phase === "settling" && (
                  <>
                    <h4>{feedbackMessage ?? "Checking your buzz…"}</h4>
                    <p>{feedback ? "Preparing the next round…" : ""}</p>
                  </>
                )}
                {phase === "animating" && (
                  <>
                    {lateBuzzIcon}
                    <h4>{feedbackMessage}</h4>
                    {lateBuzzDetail && <p>{lateBuzzDetail}</p>}
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<Play size={20} fill="currentColor" />}
                      disabled
                    >
                      Start next round
                    </Button>
                  </>
                )}
                {phase === "round_ready" && (
                  <>
                    {lateBuzzIcon}
                    <h4>{feedbackMessage}</h4>
                    {lateBuzzDetail && <p>{lateBuzzDetail}</p>}
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<Play size={20} fill="currentColor" />}
                      onClick={() => beginRef.current()}
                    >
                      Start next round
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
                      onClick={() => setAttempt((value) => value + 1)}
                    >
                      Try Halli Galli again
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
            onClick={() => setAttempt((value) => value + 1)}
          >
            Try again
          </Button>
        </div>
      )}
    </div>
  );
}
