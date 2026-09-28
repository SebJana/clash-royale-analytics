import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  CircularProgress,
  useMediaQuery,
} from "@mui/material";
import { WordleGame } from "./wordle";
import { HalliGalli } from "./halliGalli";
import { useAuth } from "../../hooks/useAuthHook";
import {
  getCaptchaId,
  getCaptchaImage,
  verifyCaptcha,
  getWordleId,
  submitWordleGuess,
  verifySecurityQuestions,
  getAuthToken,
} from "../../services/api/auth";
import "./authModal.css";

interface AuthModalProps {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly onSuccess: () => void;
}

type AuthStep = "captcha" | "wordle" | "halli_galli" | "security";
// TODO let the backend communicate that upon wordle session start and the frontend
// dynamically reacts to it
const MAX_WORDLE_GUESSES_ALLOWED = 6; // Standard Wordle guess limit

export function AuthModal({ open, onClose, onSuccess }: AuthModalProps) {
  const isNarrowScreen = useMediaQuery("(max-width:600px)");
  const [currentStep, setCurrentStep] = useState<AuthStep>("captcha");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();

  // Captcha state
  const [captchaId, setCaptchaId] = useState("");
  const [captchaImageUrl, setCaptchaImageUrl] = useState("");
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [captchaToken, setCaptchaToken] = useState("");

  // Wordle state
  const [wordleId, setWordleId] = useState("");
  const [wordleToken, setWordleToken] = useState("");
  const [halliGalliToken, setHalliGalliToken] = useState("");

  // Security questions state
  const [securityAnswers, setSecurityAnswers] = useState({
    most_annoying_card: "",
    most_skillful_card: "",
    most_mousey_card: "",
  });

  // Initialize captcha when modal opens
  useEffect(() => {
    if (open && currentStep === "captcha") {
      initializeCaptcha();
    }
  }, [open, currentStep]);

  const initializeCaptcha = async () => {
    setLoading(true);
    setError(null);
    try {
      const { captcha_id } = await getCaptchaId();
      setCaptchaId(captcha_id);

      const imageBlob = await getCaptchaImage(captcha_id);
      const imageUrl = URL.createObjectURL(imageBlob);
      setCaptchaImageUrl(imageUrl);
    } catch (err) {
      setError("Failed to load captcha");
      console.error("Captcha initialization error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCaptchaSubmit = async () => {
    if (!captchaAnswer.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const { captcha_token } = await verifyCaptcha({
        captcha_id: captchaId,
        answer: captchaAnswer,
      });
      setCaptchaToken(captcha_token);
      await initializeWordle(captcha_token);
    } catch (err) {
      setError("Incorrect captcha answer. Please try again.");
      console.error("Captcha verification error:", err);
      await initializeCaptcha(); // Reset captcha
      setCaptchaAnswer("");
    } finally {
      setLoading(false);
    }
  };

  const initializeWordle = async (token = captchaToken) => {
    setLoading(true);
    try {
      const { wordle_id } = await getWordleId(token);
      setWordleId(wordle_id);
      setCurrentStep("wordle");
    } catch (err) {
      setError("Failed to load wordle challenge");
      console.error("Wordle initialization error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleWordleGuess = async (guess: string) => {
    try {
      const result = await submitWordleGuess(captchaToken, {
        wordle_id: wordleId,
        wordle_guess: guess,
      });

      // A correct guess returns a wordle_token
      if (result.is_solution && result.wordle_token) {
        setWordleToken(result.wordle_token);
        // Don't transition immediately - let the Wordle component show success popup
        // The next step starts after the Wordle success popup is closed.
        return {
          correct: true,
          feedback: {
            evaluation: result.evaluation as Record<number, string>,
            solution: result.solution ?? "",
          },
        };
      }

      // Return feedback for incorrect guesses
      return {
        correct: false,
        feedback: {
          evaluation: result.evaluation as Record<number, string>,
          remaining_guesses: result.remaining_guesses,
          solution: result.solution ?? "",
        },
      };
    } catch (err) {
      console.error("Wordle guess error:", err);
      setError("Something went wrong, couldn't submit guess.");
      throw err;
    }
  };

  const handleWordleFailure = async () => {
    // Reset the Wordle challenge to allow retry --> request new id
    try {
      const { wordle_id } = await getWordleId(captchaToken);
      setWordleId(wordle_id);
      setError(null); // Clear any previous errors
    } catch (err) {
      setError("Failed to load new wordle challenge. Please refresh the page.");
      console.error("Wordle retry initialization error:", err);
    }
  };

  const handleWordleSuccess = () => {
    // Halli Galli must be won before security questions accept a token.
    setCurrentStep("halli_galli");
  };

  const handleHalliGalliWin = useCallback((token: string) => {
    setHalliGalliToken(token);
    setCurrentStep("security");
  }, []);

  const handleWordleExpired = useCallback(() => {
    // A rejected Wordle token cannot start another game. End this attempt so
    // the player can open authentication again from the normal entry point.
    setCurrentStep("captcha");
    setCaptchaId("");
    setCaptchaImageUrl("");
    setCaptchaAnswer("");
    setCaptchaToken("");
    setWordleId("");
    setWordleToken("");
    setHalliGalliToken("");
    onClose();
  }, [onClose]);

  const handleSecuritySubmit = async () => {
    const { most_annoying_card, most_skillful_card, most_mousey_card } =
      securityAnswers;
    if (!halliGalliToken) {
      setError("Complete Halli Galli before answering security questions.");
      return;
    }
    if (
      !most_annoying_card.trim() ||
      !most_skillful_card.trim() ||
      !most_mousey_card.trim()
    ) {
      setError("Please answer all security questions");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const { security_token } = await verifySecurityQuestions(
        halliGalliToken,
        {
          most_annoying_card,
          most_skillful_card,
          most_mousey_card,
        },
      );

      const { auth_token } = await getAuthToken(security_token);
      login(auth_token);
      resetAuthFlow();
      onSuccess();
      onClose();
    } catch (err) {
      setError("Incorrect security answers. Please try again.");
      console.error("Security questions error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Set all intermediate step values to empty and restart with captcha
  const resetAuthFlow = () => {
    setCurrentStep("captcha");
    setCaptchaId("");
    setCaptchaImageUrl("");
    setCaptchaAnswer("");
    setCaptchaToken("");
    setWordleId("");
    setWordleToken("");
    setHalliGalliToken("");
    setSecurityAnswers({
      most_annoying_card: "",
      most_skillful_card: "",
      most_mousey_card: "",
    });
    setError(null);
  };

  const handleClose = () => {
    resetAuthFlow();
    onClose();
  };

  const renderCaptchaStep = () => (
    <div className="auth-step">
      <h3 className="auth-stage-heading">Prove that you are not a robot</h3>
      {captchaImageUrl && (
        <div className="captcha-container">
          <img src={captchaImageUrl} alt="Captcha" className="captcha-image" />
          <input
            type="text"
            value={captchaAnswer}
            onChange={(e) => setCaptchaAnswer(e.target.value)}
            placeholder="Enter the text you see"
            disabled={loading}
            onKeyDown={(e) => e.key === "Enter" && handleCaptchaSubmit()}
          />
          <div className="captcha-buttons">
            <Button
              onClick={handleCaptchaSubmit}
              disabled={loading || !captchaAnswer.trim()}
              variant="contained"
              color="primary"
            >
              Verify Captcha
            </Button>
            <Button
              onClick={initializeCaptcha}
              disabled={loading}
              variant="outlined"
            >
              Refresh Captcha
            </Button>
          </div>
        </div>
      )}
    </div>
  );

  const renderWordleStep = () => (
    <div className="auth-step">
      {wordleId && (
        <WordleGame
          guessesAllowed={MAX_WORDLE_GUESSES_ALLOWED}
          onGuess={handleWordleGuess}
          onFailure={handleWordleFailure}
          onSuccess={handleWordleSuccess}
        />
      )}
    </div>
  );

  const renderHalliGalliStep = () =>
    wordleToken ? (
      <HalliGalli
        wordleToken={wordleToken}
        onWin={handleHalliGalliWin}
        onWordleExpired={handleWordleExpired}
      />
    ) : null;

  const renderSecurityStep = () => (
    <div className="auth-step">
      <h3 className="auth-stage-heading">
        Answer these questions to prove that you have elite Clash Royale
        Knowledge
      </h3>
      <div className="security-questions">
        <div className="question-group">
          <label htmlFor="annoying-card">
            What is the most annoying card in Clash Royale?
          </label>
          <input
            id="annoying-card"
            type="text"
            value={securityAnswers.most_annoying_card}
            onChange={(e) =>
              setSecurityAnswers((prev) => ({
                ...prev,
                most_annoying_card: e.target.value,
              }))
            }
            placeholder="e.g., Mega Knight"
            disabled={loading}
            autoComplete="off"
            spellCheck="false"
            data-form-type="other"
          />
        </div>
        <div className="question-group">
          <label htmlFor="skillful-card">
            What is the most skillful card in Clash Royale?
          </label>
          <input
            id="skillful-card"
            type="text"
            value={securityAnswers.most_skillful_card}
            onChange={(e) =>
              setSecurityAnswers((prev) => ({
                ...prev,
                most_skillful_card: e.target.value,
              }))
            }
            placeholder="e.g., X-Bow"
            disabled={loading}
            autoComplete="off"
            spellCheck="false"
            data-form-type="other"
          />
        </div>
        <div className="question-group">
          <label htmlFor="mousey-card">
            What is the most 'mousey/cutie/sweet' card in Clash Royale?
          </label>
          <input
            id="mousey-card"
            type="text"
            value={securityAnswers.most_mousey_card}
            onChange={(e) =>
              setSecurityAnswers((prev) => ({
                ...prev,
                most_mousey_card: e.target.value,
              }))
            }
            placeholder="e.g., Heal Spirit"
            disabled={loading}
            autoComplete="off"
            spellCheck="false"
            data-form-type="other"
          />
        </div>
        <Button
          onClick={handleSecuritySubmit}
          disabled={loading}
          variant="contained"
          className="security-submit"
        >
          Complete Authentication
        </Button>
      </div>
    </div>
  );

  const getStepContent = () => {
    switch (currentStep) {
      case "captcha":
        return renderCaptchaStep();
      case "wordle":
        return renderWordleStep();
      case "halli_galli":
        return renderHalliGalliStep();
      case "security":
        return renderSecurityStep();
      default:
        return null;
    }
  };

  return (
    <Dialog
      open={open}
      scroll={isNarrowScreen ? "body" : "paper"}
      disableEscapeKeyDown
      maxWidth={currentStep === "halli_galli" ? "lg" : "md"}
      fullWidth
      className={`auth-modal ${currentStep === "halli_galli" ? "halli-galli-modal" : currentStep === "wordle" ? "wordle-modal" : ""}`}
    >
      <DialogTitle>Authentication</DialogTitle>
      <DialogContent>
        {loading && (
          <div className="loading-overlay">
            <CircularProgress
              className="auth-loading-spinner"
              size={36}
              aria-label="Loading"
            />
          </div>
        )}
        {error && <div className="error-message">{error}</div>}
        {getStepContent()}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} color="error" variant="outlined">
          Cancel
        </Button>
      </DialogActions>
    </Dialog>
  );
}
