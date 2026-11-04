/**
 * Thin wrapper around react-native-ble-plx for the PhysioBand ESP32.
 *
 * Discovery: the firmware advertises the PhysioBand service UUID and a device name
 * "PhysioBand-XXXX". We scan without a UUID filter (some Android stacks drop 128-bit
 * filters) and accept a device if either matches.
 * Connection: connect -> request MTU 185 (a 140-byte packet needs MTU >= 143) ->
 * discover services -> read DEVICE_INFO -> subscribe to SENSOR_DATA notifications ->
 * write START_STREAM to CONTROL.
 *
 * react-native-ble-plx is a native module: it works in an Expo development build
 * (npx expo run:android / eas build), NOT in the Expo Go app.
 */
import { PermissionsAndroid, Platform } from 'react-native';
import type { BleError, Device, Subscription } from 'react-native-ble-plx';

import { BLE } from '../../constants/ble';
import type { DeviceInfo, DiscoveredDevice } from '../../types/ble';
import { base64ToBytes, bytesToAscii, bytesToBase64 } from './protocol';

type BlePlx = typeof import('react-native-ble-plx');

function loadBlePlx(): BlePlx | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require('react-native-ble-plx') as BlePlx;
  } catch {
    return null;
  }
}

export class PhysioBandBleService {
  private manager: InstanceType<BlePlx['BleManager']> | null = null;
  private plx: BlePlx | null = null;
  readonly unavailableReason: string | null = null;

  constructor() {
    this.plx = loadBlePlx();
    try {
      if (this.plx) this.manager = new this.plx.BleManager();
    } catch {
      this.manager = null;
    }
    if (!this.manager) {
      this.unavailableReason =
        'Bluetooth module not found. BLE requires an Expo development build (npx expo run:android), not Expo Go.';
    }
  }

  get available(): boolean {
    return this.manager !== null;
  }

  onStateChange(listener: (state: string) => void): Subscription | null {
    return this.manager?.onStateChange((s) => listener(String(s)), true) ?? null;
  }

  async requestPermissions(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;
    const api = typeof Platform.Version === 'number' ? Platform.Version : parseInt(String(Platform.Version), 10);
    if (api >= 31) {
      const result = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
      ]);
      return Object.values(result).every((r) => r === PermissionsAndroid.RESULTS.GRANTED);
    }
    const fine = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION);
    return fine === PermissionsAndroid.RESULTS.GRANTED;
  }

  /** Start scanning. Returns a function that stops the scan. */
  scan(onDevice: (d: DiscoveredDevice) => void, onError: (message: string) => void): () => void {
    if (!this.manager) {
      onError(this.unavailableReason ?? 'Bluetooth unavailable');
      return () => undefined;
    }
    const seen = new Set<string>();
    this.manager.startDeviceScan(null, { allowDuplicates: false }, (error: BleError | null, device: Device | null) => {
      if (error) {
        onError(error.message);
        return;
      }
      if (!device) return;
      const name = device.name ?? device.localName ?? '';
      const matchesService = (device.serviceUUIDs ?? []).some((u) => u.toLowerCase() === BLE.SERVICE_UUID);
      if (!matchesService && !name.startsWith(BLE.DEVICE_NAME_PREFIX)) return;
      if (seen.has(device.id)) return;
      seen.add(device.id);
      onDevice({ id: device.id, name: name || 'PhysioBand', rssi: device.rssi ?? null });
    });
    return () => {
      void this.manager?.stopDeviceScan();
    };
  }

  async connect(id: string): Promise<{ device: Device; info: DeviceInfo | null }> {
    if (!this.manager) throw new Error(this.unavailableReason ?? 'Bluetooth unavailable');
    await this.manager.stopDeviceScan();
    let device = await this.manager.connectToDevice(id, { timeout: 10000, requestMTU: BLE.REQUESTED_MTU });
    if (Platform.OS === 'android' && (device.mtu ?? 23) < BLE.REQUESTED_MTU) {
      try {
        device = await device.requestMTU(BLE.REQUESTED_MTU);
      } catch {
        // keep the negotiated MTU; firmware adapts the number of samples per packet
      }
    }
    device = await device.discoverAllServicesAndCharacteristics();
    let info: DeviceInfo | null = null;
    try {
      const ch = await device.readCharacteristicForService(BLE.SERVICE_UUID, BLE.DEVICE_INFO_UUID);
      if (ch.value) info = JSON.parse(bytesToAscii(base64ToBytes(ch.value))) as DeviceInfo;
    } catch {
      info = null;
    }
    return { device, info };
  }

  monitor(device: Device, onValue: (base64: string) => void, onError: (message: string) => void): Subscription {
    return device.monitorCharacteristicForService(BLE.SERVICE_UUID, BLE.SENSOR_DATA_UUID, (error, ch) => {
      if (error) {
        onError(error.message);
        return;
      }
      if (ch?.value) onValue(ch.value);
    });
  }

  async sendCommand(device: Device, command: number): Promise<void> {
    await device.writeCharacteristicWithResponseForService(
      BLE.SERVICE_UUID,
      BLE.CONTROL_UUID,
      bytesToBase64(new Uint8Array([command])),
    );
  }

  onDisconnected(id: string, listener: (error: string | null) => void): Subscription | null {
    return this.manager?.onDeviceDisconnected(id, (error) => listener(error?.message ?? null)) ?? null;
  }

  async disconnect(id: string): Promise<void> {
    try {
      await this.manager?.cancelDeviceConnection(id);
    } catch {
      // already disconnected
    }
  }

  destroy(): void {
    void this.manager?.destroy();
  }
}
