import { useState, useEffect, useCallback } from "react";
import { isValidGuess } from "../../utils/wordle";
import "./wordle.css";

// Props for Wordle game component
interface WordleGameProps {
  readonly guessesAllowed: number; // Maximum number of guesses
  readonly onGuess: (guess: string) => Promise<{
    correct: boolean;
    feedback?: { evaluation: Record<number, string> };
  }>; // Callback to validate guess and get feedback
  readonly onFailure: () => void; // Callback when all guesses are exhausted
}

const WORDLE_WORD_LENGTH = 5;

/**
 * Wordle game component for authentication challenge
 */
export function WordleGame({
  guessesAllowed,
  onGuess,
  onFailure,
}: WordleGameProps) {
  const [guesses, setGuesses] = useState<string[]>([]); // All submitted guesses
  const [evaluations, setEvaluations] = useState<string[][]>([]); // Color feedback for each guess
  const [currentGuess, setCurrentGuess] = useState(""); // Current input being typed
  const [gameStatus, setGameStatus] = useState<"playing" | "won" | "lost">(
    "playing"
  );
  const [isSubmitting, setIsSubmitting] = useState(false); // Loading state for API calls

  // Handle guess submission and evaluation
  const handleSubmit = useCallback(async () => {
    if (currentGuess.length !== WORDLE_WORD_LENGTH || isSubmitting) return;

    // Validate guess before submitting - silently block if invalid
    // TODO add not in word list pop up and letter boxes shake animation?
    try {
      const isValid = await isValidGuess(currentGuess);
      if (!isValid) {
        return; // Simply block the submission of the invalid guess
      }
    } catch (error) {
      console.error("Error validating guess:", error);
      return; // Block submission on validation error
    }

    setIsSubmitting(true);
    try {
      const result = await onGuess(currentGuess);
      const newGuesses = [...guesses, currentGuess];
      setGuesses(newGuesses);

      // Convert backend evaluation to CSS classes for visual feedback
      if (result.feedback?.evaluation) {
        // Convert evaluation object to array and map backend values to CSS classes
        const evaluationArray: string[] = [];
        for (let i = 0; i < WORDLE_WORD_LENGTH; i++) {
          const backendValue = result.feedback.evaluation[i];
          let cssClass = "";

          switch (backendValue) {
            case "correct":
              cssClass = "correct";
              break;
            case "in word":
              cssClass = "present";
              break;
            case "wrong":
              cssClass = "absent";
              break;
            default:
              cssClass = "filled";
          }

          evaluationArray.push(cssClass);
        }

        const newEvaluations = [...evaluations, evaluationArray];
        setEvaluations(newEvaluations);
      }

      // Check win/lose conditions
      if (result.correct) {
        setGameStatus("won");
      } else if (newGuesses.length >= guessesAllowed) {
        setGameStatus("lost");
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
    onGuess,
    guesses,
    evaluations,
    guessesAllowed,
    onFailure,
  ]);

  // Handle keyboard input for typing letters, backspace, and enter
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (gameStatus === "playing") {
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
  }, [gameStatus, handleSubmit, currentGuess.length, isSubmitting]);

  return (
    <div className="wordle-game">
      <h3>
        Solve the Wordle to prove you're worthy of managing player tracking
      </h3>
      <p>You have {guessesAllowed} attempts.</p>

      {/* TODO better visual feedback for invalid guess and one by one filling of letters */}

      <div className="wordle-grid">
        {/* Render game grid with rows for each guess attempt */}
        {Array.from({ length: guessesAllowed }, (_, i) => (
          <div key={i} className="wordle-row">
            {Array.from({ length: WORDLE_WORD_LENGTH }, (_, j) => {
              let letter = "";
              if (i < guesses.length) {
                letter = guesses[i][j] || "";
              } else if (i === guesses.length) {
                letter = currentGuess[j] || "";
              }

              // Apply appropriate CSS class based on evaluation state
              let cellClass = "wordle-cell ";
              if (i < guesses.length) {
                // Apply evaluation-based colors for completed guesses
                if (evaluations[i]?.[j]) {
                  cellClass += evaluations[i][j]; // 'correct', 'present', or 'absent'
                } else {
                  cellClass += "filled";
                }
              } else if (i === guesses.length) {
                cellClass += "current";
              } else {
                cellClass += "empty";
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

      {/* TODO add keyboard layout showing the remaining letters and their colors 
          Keyboard would have to mirror local layout of the user tho, as long as it is english compatible*/}

      <div className="wordle-input-area">
        <input
          type="text"
          value={currentGuess}
          readOnly
          maxLength={WORDLE_WORD_LENGTH}
          placeholder={`Enter ${WORDLE_WORD_LENGTH}-letter word`}
          disabled={gameStatus !== "playing" || isSubmitting}
          autoFocus
        />
        <button
          onClick={handleSubmit}
          disabled={
            currentGuess.length !== WORDLE_WORD_LENGTH ||
            gameStatus !== "playing" ||
            isSubmitting
          }
        >
          {isSubmitting ? "Submitting..." : "Submit"}
        </button>
      </div>

      <div className="wordle-status">
        <p>
          Guesses used: {guesses.length} / {guessesAllowed}
        </p>
        {/* TODO upon game end show screen with continue (win) or restart and answer (loss)  */}
      </div>
    </div>
  );
}
