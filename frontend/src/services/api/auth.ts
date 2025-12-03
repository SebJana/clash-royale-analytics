import api from "./axios";
import type {
  CaptchaResponse,
  CaptchaVerifyRequest,
  CaptchaTokenResponse,
  WordleResponse,
  WordleVerifyRequest,
  SecurityQuestionsRequest,
  SecurityTokenResponse,
  AuthTokenResponse,
} from "../../types/auth";

// Step 1: Captcha
// Step 1.1: Get captcha ID
export async function getCaptchaId(): Promise<CaptchaResponse> {
  const response = await api.get<CaptchaResponse>("/auth/captcha_id");
  return response.data;
}

// Step 1.2: Get captcha image
export async function getCaptchaImage(captchaId: string): Promise<Blob> {
  const response = await api.get(`/auth/captcha_image/${captchaId}`, {
    responseType: "blob",
  });
  return response.data;
}

// Step 1.3: Verify captcha and get captcha token
export async function verifyCaptcha(
  request: CaptchaVerifyRequest
): Promise<CaptchaTokenResponse> {
  const response = await api.post<CaptchaTokenResponse>(
    "/auth/verify_captcha",
    request
  );
  return response.data;
}

// Step 2: Wordle
// Step 2.1: Get wordle challenge ID
export async function getWordleId(): Promise<WordleResponse> {
  const response = await api.get<WordleResponse>("/auth/wordle_id");
  return response.data;
}

// Step 2.2: Submit wordle guess and get evaluation/feedback
export async function submitWordleGuess(request: WordleVerifyRequest): Promise<{
  evaluation: unknown;
  remaining_guesses: number;
  is_solution: boolean;
  wordle_token?: string;
  solution?: string;
}> {
  const response = await api.post("/auth/verify_wordle", request);
  return response.data;
}

// Step 3: Verify security questions and get security token
export async function verifySecurityQuestions(
  request: SecurityQuestionsRequest
): Promise<SecurityTokenResponse> {
  const response = await api.post<SecurityTokenResponse>(
    "/auth/verify_security_questions",
    request
  );
  return response.data;
}

// Step 4: Get final auth token
export async function getAuthToken(
  securityToken: string
): Promise<AuthTokenResponse> {
  const response = await api.post<AuthTokenResponse>("/auth/token", {
    security_token: securityToken,
  });
  return response.data;
}

// Utility: Set auth token in axios headers
export function setAuthToken(token: string): void {
  api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
}

// Utility: Clear auth token from axios headers
export function clearAuthToken(): void {
  delete api.defaults.headers.common["Authorization"];
}
