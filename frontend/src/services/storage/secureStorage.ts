/**
 * Token and small preference storage. On Android / iOS the JWT is kept in the OS
 * keystore via expo-secure-store. The web build (UI preview only) falls back to
 * localStorage because SecureStore has no web implementation.
 */
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const KEYS = {
  token: 'physioband.access_token',
  lastDevice: 'physioband.last_device',
  serverUrl: 'physioband.server_url',
};

const isWeb = Platform.OS === 'web';
const store = {
  get: (k: string) => (isWeb ? Promise.resolve(globalThis.localStorage?.getItem(k) ?? null) : SecureStore.getItemAsync(k)),
  set: (k: string, v: string) => (isWeb ? Promise.resolve(globalThis.localStorage?.setItem(k, v)) : SecureStore.setItemAsync(k, v)),
  del: (k: string) => (isWeb ? Promise.resolve(globalThis.localStorage?.removeItem(k)) : SecureStore.deleteItemAsync(k)),
};

export const secureStorage = {
  getToken: () => store.get(KEYS.token),
  setToken: (token: string) => store.set(KEYS.token, token),
  clearToken: () => store.del(KEYS.token),

  async getLastDevice(): Promise<{ id: string; name: string } | null> {
    const raw = await store.get(KEYS.lastDevice);
    try {
      return raw ? (JSON.parse(raw) as { id: string; name: string }) : null;
    } catch {
      return null;
    }
  },
  setLastDevice: (device: { id: string; name: string }) => store.set(KEYS.lastDevice, JSON.stringify(device)),
  clearLastDevice: () => store.del(KEYS.lastDevice),

  getServerUrl: () => store.get(KEYS.serverUrl),
  setServerUrl: (url: string) => store.set(KEYS.serverUrl, url),
  clearServerUrl: () => store.del(KEYS.serverUrl),
};
