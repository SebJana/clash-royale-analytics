import type { HalliGalliRevealResponse } from "../../types/auth";
import { gcm } from "@noble/ciphers/aes.js";

export type EncryptedCard = {
  image: Blob;
  imageVersion: number;
  imageId: string;
};

/**
 * Run the server's connection test and return the short-lived ID for game start.
 * Browser WebSockets cannot set Authorization, so the Wordle token goes in the
 * first frame. The server checks it before sending timing probes. Abort closes
 * the socket when the modal closes or a new attempt replaces this one.
 */
export function calibrateHalliGalli(
  wordleToken: string,
  signal: AbortSignal,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = new URL(
      "/api/auth/halli-galli/calibration",
      window.location.href,
    );
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(url);
    let finished = false;
    const timeout = window.setTimeout(
      () => fail("Connection test timed out."),
      20000,
    );
    const abort = () => fail("Connection test cancelled.");
    signal.addEventListener("abort", abort, { once: true });

    // One completion path owns socket and listener cleanup. Close/error events
    // can arrive after a successful result, so only the first one may settle.
    function finish() {
      window.clearTimeout(timeout);
      signal.removeEventListener("abort", abort);
      socket.close();
      finished = true;
    }
    function fail(message: string) {
      if (finished) return;
      finish();
      reject(new Error(message));
    }
    socket.onopen = () =>
      socket.send(
        JSON.stringify({ type: "authenticate", wordle_token: wordleToken }),
      );
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (
          message.type === "probe" &&
          Number.isInteger(message.sequence) &&
          typeof message.nonce === "string"
        ) {
          socket.send(
            JSON.stringify({
              type: "pong",
              sequence: message.sequence,
              nonce: message.nonce,
            }),
          );
        } else if (
          message.type === "calibration_complete" &&
          typeof message.calibration_id === "string"
        ) {
          finish();
          resolve(message.calibration_id);
        } else if (message.type === "calibration_failed") {
          fail(`Connection test failed: ${message.reason ?? "unknown error"}.`);
        }
      } catch {
        fail("Connection test returned an invalid message.");
      }
    };
    socket.onerror = () => fail("Connection test could not connect.");
    socket.onclose = () => {
      if (!finished) fail("Connection test closed early.");
    };
    if (signal.aborted) abort();
  });
}

/**
 * Check the ID and version together before using a reveal key. Another preload
 * for this round would replace the server's key and make older bytes unusable.
 */
export function matchingCard(
  card: EncryptedCard,
  reveal: HalliGalliRevealResponse,
): boolean {
  return (
    card.imageId === reveal.image_id &&
    card.imageVersion === reveal.image_version
  );
}

/**
 * Decrypt a PNG whose first 12 bytes are the AES-GCM nonce and whose remaining
 * bytes include the ciphertext and authentication tag. The caller owns the
 * returned object URL and must revoke it after removing the card.
 * Web Crypto needs HTTPS or localhost. On a LAN HTTP address, use the same
 * authenticated AES-GCM decryption in JavaScript so local Docker hosting works
 * without asking every test device to trust a certificate. This does not make
 * HTTP private: tokens and game requests still cross the LAN without TLS.
 */
export async function decryptHalliGalliCard(
  card: EncryptedCard,
  keyBase64: string,
): Promise<string> {
  const bytes = new Uint8Array(await card.image.arrayBuffer());
  if (bytes.length < 29) throw new Error("The encrypted card is incomplete.");
  const keyBytes = Uint8Array.from(atob(keyBase64), (character) =>
    character.charCodeAt(0),
  );
  const nonce = bytes.slice(0, 12);
  const ciphertext = bytes.slice(12);
  const image = globalThis.crypto?.subtle
    ? await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: nonce },
        await crypto.subtle.importKey("raw", keyBytes, "AES-GCM", false, [
          "decrypt",
        ]),
        ciphertext,
      )
    : gcm(keyBytes, nonce).decrypt(ciphertext);
  return URL.createObjectURL(new Blob([image], { type: "image/png" }));
}
