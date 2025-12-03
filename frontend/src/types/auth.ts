export type CaptchaResponse = {
  captcha_id: string;
};

export type CaptchaVerifyRequest = {
  captcha_id: string;
  answer: string;
};

export type CaptchaTokenResponse = {
  captcha_token: string;
};

export type WordleResponse = {
  wordle_id: string;
};

export type WordleVerifyRequest = {
  captcha_token: string;
  wordle_id: string;
  wordle_guess: string;
};

export type SecurityQuestionsRequest = {
  wordle_token: string;
  most_annoying_card: string;
  most_skillful_card: string;
  most_mousey_card: string;
};

export type SecurityTokenResponse = {
  security_token: string;
};

export type AuthTokenResponse = {
  auth_token: string;
};

export type AuthState = {
  isAuthenticated: boolean;
  authToken?: string;
  expiresAt?: number;
};
