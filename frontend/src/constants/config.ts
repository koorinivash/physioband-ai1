/**
 * Runtime configuration. Set EXPO_PUBLIC_API_URL in frontend/.env, e.g.
 *   EXPO_PUBLIC_API_URL=http://192.168.1.20:8000/api/v1   (backend on your PC, same Wi-Fi)
 *   EXPO_PUBLIC_API_URL=https://your-backend.example.com/api/v1
 */
/** Hosted backend on Render (see render.yaml). Can be changed inside the app on the sign-in screen. */
export const DEFAULT_API_URL = 'https://physioband-ai-api.onrender.com/api/v1';

/** Server URL baked in at build time; the user can override it at runtime (stored on the device). */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? DEFAULT_API_URL).replace(/\/$/, '');

export function normalizeApiUrl(input: string): string {
  let url = input.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
  if (!/\/api\/v1$/.test(url)) url = `${url}/api/v1`;
  return url;
}

export const UPLOAD = {
  /** Samples are uploaded to the backend roughly once per second (50 samples at 50 Hz). */
  INTERVAL_MS: 1000,
  MAX_BATCH_SAMPLES: 400,
  /** Give up on a workout upload queue that cannot be delivered after this many queued batches. */
  MAX_QUEUED_BATCHES: 600,
  // Long enough for a sleeping Render free-tier instance to wake up (~30-60 s).
  REQUEST_TIMEOUT_MS: 60000,
};

export const RECONNECT = {
  ATTEMPTS: 5,
  DELAY_MS: 2500,
};
