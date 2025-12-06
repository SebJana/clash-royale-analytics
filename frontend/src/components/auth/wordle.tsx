import { useState, useEffect, useCallback } from "react";
import { isValidGuess } from "../../utils/wordle";
import "./wordle.css";

// Props for Wordle game component
interface WordleGameProps {
  readonly guessesAllowed: number; // Maximum number of guesses
  readonly onGuess: (guess: string) => Promise<{
    correct: boolean;
    feedback?: { evaluation: Record<number, string>; solution: string };
  }>; // Callback to validate guess and get feedback
  readonly onFailure: () => void; // Callback when all guesses are exhausted
  readonly onSuccess?: () => void; // Callback when the wordle is solved
}

const WORDLE_WORD_LENGTH = 5;
const FLIP_DURATION_MS = 800; // Individual letter flip animation duration
const FLIP_DELAY_LETTER_MS = 400; // Stagger delay between letter flips

// Keyboard layout for Wordle (always use American 'QWERTY' layout)
const KEYBOARD_ROWS = [
  ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
  ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
  ["ENTER", "Z", "X", "C", "V", "B", "N", "M", "BACKSPACE"],
];

/**
 * Wordle game component for authentication challenge
 */
export function WordleGame({
  guessesAllowed,
  onGuess,
  onFailure,
  onSuccess,
}: WordleGameProps) {
  const [guesses, setGuesses] = useState<string[]>([]);
  const [evaluations, setEvaluations] = useState<string[][]>([]);
  const [currentGuess, setCurrentGuess] = useState("");
  const [gameStatus, setGameStatus] = useState<"playing" | "won" | "lost">(
    "playing"
  );
  const [solution, setSolution] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [letterStates, setLetterStates] = useState<Record<string, string>>({});
  const [shakeCurrentRow, setShakeCurrentRow] = useState(false); // Invalid guess animation
  const [showGameEndPopup, setShowGameEndPopup] = useState(false);

  // Animation state management for flip reveal
  const [animatingRowIndex, setAnimatingRowIndex] = useState<number | null>(
    null
  );
  const [animatingLetterIndex, setAnimatingLetterIndex] = useState(-1);
  const [completedLetterIndex, setCompletedLetterIndex] = useState(-1); // Controls when colors show
  const [isAnimationRunning, setIsAnimationRunning] = useState(false); // Prevents input during animations

  // Orchestrates staggered flip animations for guess feedback
  const animateLetterReveal = useCallback((rowIndex: number) => {
    setAnimatingRowIndex(rowIndex);
    setAnimatingLetterIndex(0);
    setCompletedLetterIndex(-1);
    setIsAnimationRunning(true);

    // Stagger each letter's flip animation
    for (let i = 0; i < WORDLE_WORD_LENGTH; i++) {
      // Start flip - Each letter starts after previous letter's delay
      // Letter 0: 0ms, Letter 1: 400ms, Letter 2: 800ms, etc.
      setTimeout(() => {
        setAnimatingLetterIndex(i);
      }, i * FLIP_DELAY_LETTER_MS);

      // Show color before flip completes (80% through the animation)
      // Calculation: (letter_index * delay) + (80% of flip_duration)
      // This reveals color while card is rotating back to face, creating smooth reveal
      // Example: Letter 2 shows color at 800ms + 640ms = 1440ms
      setTimeout(() => {
        setCompletedLetterIndex(i);
      }, i * FLIP_DELAY_LETTER_MS + FLIP_DURATION_MS * 0.8);
    }

    // Clean up after all animations finish
    // Calculation: (5 letters * 400ms delay) + 5000ms buffer = 7000ms total
    // Buffer ensures all flip animations (800ms each) complete before cleanup
    setTimeout(() => {
      setAnimatingRowIndex(null);
      setAnimatingLetterIndex(-1);
      setCompletedLetterIndex(-1);
      setIsAnimationRunning(false);
    }, WORDLE_WORD_LENGTH * FLIP_DELAY_LETTER_MS + 5000);

    // Safety unlock - Shorter timeout to prevent stuck input if main cleanup fails
    // Uses 1000ms buffer instead of 5000ms as emergency fallback
    setTimeout(() => {
      setIsAnimationRunning(false);
    }, WORDLE_WORD_LENGTH * FLIP_DELAY_LETTER_MS + 1000);
  }, []);

  // Emergency timeout to prevent permanent input lock
  useEffect(() => {
    if (isAnimationRunning) {
      const emergencyTimeout = setTimeout(() => {
        setIsAnimationRunning(false);
      }, 5000);
      return () => clearTimeout(emergencyTimeout);
    }
  }, [isAnimationRunning]);

  // Validates guess, submits to API, and triggers animations
  const handleSubmit = useCallback(async () => {
    if (
      currentGuess.length !== WORDLE_WORD_LENGTH ||
      isSubmitting ||
      isAnimationRunning
    )
      return;

    // Block invalid guesses with shake animation
    try {
      const isValid = await isValidGuess(currentGuess);
      if (!isValid) {
        setShakeCurrentRow(true);
        setTimeout(() => setShakeCurrentRow(false), 500);
        return;
      }
    } catch (error) {
      console.error("Error validating guess:", error);
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await onGuess(currentGuess);
      setSolution(result.feedback?.solution ?? ""); // Save solution, if it is present in result
      const newGuesses = [...guesses, currentGuess];
      setGuesses(newGuesses);

      // Convert backend evaluation to CSS classes for visual feedback
      if (result.feedback?.evaluation) {
        // Transform backend response format to frontend array structure
        // Backend: {0: "correct", 1: "in word", 2: "wrong"}
        // Frontend: ["correct", "present", "absent"]
        const evaluationArray: string[] = [];
        for (let i = 0; i < WORDLE_WORD_LENGTH; i++) {
          const backendValue = result.feedback.evaluation[i];
          let cssClass = "";

          // Map backend terminology to CSS class names that match our styles
          // "in word" becomes "present" to align with Wordle conventions
          switch (backendValue) {
            case "correct":
              cssClass = "correct"; // Green - letter in correct position
              break;
            case "in word":
              cssClass = "present"; // Yellow - letter in word but wrong position
              break;
            case "wrong":
              cssClass = "absent"; // Gray - letter not in word at all
              break;
            default:
              cssClass = "filled"; // Fallback for unexpected values
          }

          evaluationArray.push(cssClass);
        }

        const newEvaluations = [...evaluations, evaluationArray];

        // Start the flip animation for the current row
        const currentRowIndex = newGuesses.length - 1;
        animateLetterReveal(currentRowIndex);

        // Set evaluations immediately but animation will control visual reveal
        setEvaluations(newEvaluations);

        // Update letter states for keyboard after animation completes
        // Wait for all flip animations to finish before updating keyboard colors
        // Timeout matches the last letter's completion: (4 * 400ms) + (800ms * 0.8) = 2240ms
        setTimeout(() => {
          const newLetterStates = { ...letterStates };
          for (let i = 0; i < WORDLE_WORD_LENGTH; i++) {
            const letter = currentGuess[i];
            const state = evaluationArray[i];

            // Implement letter state priority system to handle repeated letters
            // Priority hierarchy: correct > present > absent > unused
            // Example: If 'A' was 'absent' before but now 'correct', upgrade to 'correct'
            // But if 'A' was 'correct' before and now 'present', keep 'correct'
            if (
              !newLetterStates[letter] || // First time seeing this letter
              state === "correct" || // Always upgrade to correct
              (state === "present" && newLetterStates[letter] === "absent") // Upgrade absent to present
            ) {
              newLetterStates[letter] = state;
            }
          }
          setLetterStates(newLetterStates);
        }, WORDLE_WORD_LENGTH * FLIP_DELAY_LETTER_MS);
      }

      // Check win/lose conditions and schedule popup display
      if (result.correct) {
        setGameStatus("won");
        // Calculate when to show popup: wait for all flips to start + buffer for user to see result
        // Formula: (5 letters * 400ms stagger) + 1000ms buffer = 3000ms total
        // This ensures user sees the final letter flip and has time to process the win
        const animationDuration =
          WORDLE_WORD_LENGTH * FLIP_DELAY_LETTER_MS + 1000;
        setTimeout(() => {
          setShowGameEndPopup(true);
        }, animationDuration);
      } else if (newGuesses.length >= guessesAllowed) {
        setGameStatus("lost");
        // Use same timing calculation for consistency in user experience
        // Player gets to see their final guess result before failure message
        const animationDuration =
          WORDLE_WORD_LENGTH * FLIP_DELAY_LETTER_MS + 1000;
        setTimeout(() => {
          setShowGameEndPopup(true);
        }, animationDuration);
        onFailure();
      }

      setCurrentGuess("");
    } catch (error) {
      console.error("Error submitting guess:", error);
    } finally {
      setIsSubmitting(false);
    }
  }, [
    currentGuess,
    isSubmitting,
    isAnimationRunning,
    onGuess,
    guesses,
    evaluations,
    guessesAllowed,
    onFailure,
    letterStates,
    animateLetterReveal,
  ]);

  // Handle displayed keyboard input
  const handleKeyboardInput = useCallback(
    (key: string) => {
      if (gameStatus !== "playing" || isAnimationRunning) return;

      if (key === "ENTER") {
        if (currentGuess.length === WORDLE_WORD_LENGTH && !isSubmitting) {
          handleSubmit();
        }
      } else if (key === "BACKSPACE") {
        setCurrentGuess((prev) => prev.slice(0, -1));
      } else if (/^[A-Z]$/.test(key)) {
        if (currentGuess.length < WORDLE_WORD_LENGTH) {
          setCurrentGuess((prev) => prev + key);
        }
      }
    },
    [
      gameStatus,
      handleSubmit,
      currentGuess.length,
      isSubmitting,
      isAnimationRunning,
    ]
  );

  // Handle actual keyboard input for typing letters, backspace, and enter
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (gameStatus === "playing" && !isAnimationRunning) {
        if (event.key === "Enter") {
          // Submit guess when Enter is pressed
          if (currentGuess.length === WORDLE_WORD_LENGTH && !isSubmitting) {
            handleSubmit();
          }
        } else if (event.key === "Backspace") {
          // Remove last character
          setCurrentGuess((prev) => prev.slice(0, -1));
        } else if (/^[a-zA-Z]$/.test(event.key)) {
          // Add letter if within word length limit
          if (currentGuess.length < WORDLE_WORD_LENGTH) {
            setCurrentGuess((prev) => prev + event.key.toUpperCase());
          }
        }
      }
    };

    globalThis.addEventListener("keydown", handleKeyDown);
    return () => globalThis.removeEventListener("keydown", handleKeyDown);
  }, [
    gameStatus,
    handleSubmit,
    currentGuess.length,
    isSubmitting,
    isAnimationRunning,
  ]);

  return (
    <div className="wordle-game">
      <h3>
        Solve the Wordle to prove you're worthy of managing player tracking
      </h3>

      <div className="wordle-grid">
        {/* Render game grid with rows for each guess attempt */}
        {Array.from({ length: guessesAllowed }, (_, i) => (
          <div
            key={i}
            className={`wordle-row ${
              i === guesses.length && shakeCurrentRow ? "shake" : ""
            }`}
          >
            {Array.from({ length: WORDLE_WORD_LENGTH }, (_, j) => {
              let letter = "";
              if (i < guesses.length) {
                letter = guesses[i][j] || "";
              } else if (i === guesses.length) {
                letter = currentGuess[j] || "";
              }

              // Determine cell styling based on animation state
              let cellClass = "wordle-cell ";

              // Animation logic: controls flip timing and color reveal
              // Complex state machine that determines when each letter should animate and show colors

              // shouldStartFlip: Has this letter's animation been triggered?
              // True when: we're animating this row AND the animation has reached or passed this letter
              // Example: Row 2, Letter 3 starts flipping when animatingLetterIndex >= 3
              const shouldStartFlip =
                animatingRowIndex === i && animatingLetterIndex >= j;

              // hasCompletedFlip: Should this letter show its final color?
              // For animating rows: True when completedLetterIndex has reached this letter
              // For non-animating rows: Always true (they show colors immediately)
              // This creates the delayed color reveal effect during animations
              const hasCompletedFlip =
                animatingRowIndex === i ? completedLetterIndex >= j : true;

              // isCurrentlyFlipping: Is this letter actively in its flip animation?
              // True when: animation started for this letter BUT color hasn't been revealed yet
              // This triggers the CSS flip class for the visual rotation effect
              const isCurrentlyFlipping = shouldStartFlip && !hasCompletedFlip;

              if (i < guesses.length) {
                // Colors only show after flip animation reaches completion point
                if (evaluations[i]?.[j] && hasCompletedFlip) {
                  cellClass += evaluations[i][j]; // 'correct', 'present', or 'absent'
                } else {
                  cellClass += "filled";
                }

                // Active flip animation class
                if (isCurrentlyFlipping) {
                  cellClass += " flip";
                }
              } else if (i === guesses.length) {
                cellClass += "current"; // Currently typing row
              } else {
                cellClass += "empty"; // Future guess rows
              }

              return (
                <div key={j} className={cellClass}>
                  {letter}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      {/* Wordle keyboard */}
      <div className="wordle-keyboard">
        {KEYBOARD_ROWS.map((row) => (
          <div key={row.join("")} className="keyboard-row">
            {row.map((key) => (
              <button
                key={key}
                className={`keyboard-key ${
                  key === "ENTER" || key === "BACKSPACE" ? "wide" : ""
                } ${letterStates[key] || ""}`}
                onClick={() => handleKeyboardInput(key)}
                disabled={
                  gameStatus !== "playing" || isSubmitting || isAnimationRunning
                }
              >
                {key === "BACKSPACE" ? "⌫" : key}
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* Game end popup for win/loss */}
      {showGameEndPopup && (
        <div className="game-end-popup">
          <div className="popup-content">
            {gameStatus === "won" ? (
              <>
                <h2>🎉 Solved! 🎉</h2>
                <p>Congratulations! You've proven your worth!</p>
                <button
                  className="popup-button continue-button"
                  onClick={() => {
                    setShowGameEndPopup(false);
                    onSuccess?.();
                  }}
                >
                  Continue
                </button>
              </>
            ) : (
              <>
                <h2>Game Over</h2>
                <p>
                  The correct solution was:{" "}
                  <strong>{solution.toUpperCase()}</strong>
                </p>
                <button
                  className="popup-button retry-button"
                  onClick={() => {
                    setShowGameEndPopup(false);
                    // Reset game state for retry
                    setGuesses([]);
                    setEvaluations([]);
                    setCurrentGuess("");
                    setGameStatus("playing");
                    setLetterStates({});
                    // Call onFailure to restart challenge
                    onFailure();
                  }}
                >
                  Try Again
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
