import axios, { AxiosError } from 'axios';

import { API_URL, UPLOAD } from '../../constants/config';
import type { ApiErrorBody } from '../../types/api';

export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number | null,
    public details?: unknown,
  ) {
    super(message);
  }

  /** True when the request never reached the server (offline, wrong URL, timeout). */
  get isNetworkError(): boolean {
    return this.status === null;
  }
}

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

/** Switch the backend at runtime (server address setting). */
export function setApiBaseUrl(url: string) {
  http.defaults.baseURL = url;
}

export function getApiBaseUrl(): string {
  return http.defaults.baseURL ?? API_URL;
}

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

export const http = axios.create({
  baseURL: API_URL,
  timeout: UPLOAD.REQUEST_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

http.interceptors.request.use((config) => {
  if (authToken) config.headers.Authorization = `Bearer ${authToken}`;
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => {
    if (!error.response) {
      const timeout = error.code === 'ECONNABORTED';
      return Promise.reject(
        new ApiError(
          timeout
            ? 'The server took too long to respond.'
            : `Cannot reach the PhysioBand server at ${getApiBaseUrl()}. Check your internet connection or the server address.`,
          timeout ? 'TIMEOUT' : 'NETWORK_ERROR',
          null,
        ),
      );
    }
    const { status, data } = error.response;
    const body = data?.error;
    if (status === 401 && authToken && body?.code !== 'INVALID_CREDENTIALS') onUnauthorized?.();
    return Promise.reject(
      new ApiError(body?.message ?? `Request failed (${status})`, body?.code ?? 'HTTP_ERROR', status, body?.details),
    );
  },
);

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Something went wrong';
}
