export type BleConnectionState =
  | 'unavailable' // native BLE module missing (e.g. Expo Go) or unsupported hardware
  | 'bluetooth_off'
  | 'unauthorized'
  | 'idle'
  | 'scanning'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected';

export interface DiscoveredDevice {
  id: string; // platform BLE identifier (MAC on Android, UUID on iOS)
  name: string;
  rssi: number | null;
}

export interface DeviceInfo {
  device_id: string;
  name: string;
  firmware: string;
  protocol: number;
  sample_rate_hz: number;
  max_samples_per_packet: number;
}

export interface DecodedPacket {
  version: number;
  sequence: number;
  deviceId: number;
  samples: import('./api').SensorSample[];
}
