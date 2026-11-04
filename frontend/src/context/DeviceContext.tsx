/**
 * Global BLE device state: scanning, connection, automatic reconnection and the
 * decoded sensor stream. Screens subscribe to raw samples with `subscribeSamples`;
 * lightweight sensor health is published to React state at ~4 Hz so the UI does not
 * re-render 50 times per second.
 */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { Device, Subscription } from 'react-native-ble-plx';

import { BLE, COMMANDS, STATUS_BITS } from '../constants/ble';
import { RECONNECT } from '../constants/config';
import { deviceApi } from '../services/api/endpoints';
import { PhysioBandBleService } from '../services/ble/bleService';
import { decodeBase64Packet, PacketError } from '../services/ble/protocol';
import { secureStorage } from '../services/storage/secureStorage';
import type { SensorSample } from '../types/api';
import type { BleConnectionState, DeviceInfo, DiscoveredDevice } from '../types/ble';
import { useAuth } from './AuthContext';

export interface SensorHealth {
  receiving: boolean;
  packetsPerSecond: number;
  samplesPerSecond: number;
  upperArmOk: boolean;
  forearmOk: boolean;
  loadCellOk: boolean;
  loadCellCalibrated: boolean;
  gyroCalibrated: boolean;
  lastSample: SensorSample | null;
  invalidPackets: number;
  lostPackets: number;
}

const EMPTY_HEALTH: SensorHealth = {
  receiving: false,
  packetsPerSecond: 0,
  samplesPerSecond: 0,
  upperArmOk: false,
  forearmOk: false,
  loadCellOk: false,
  loadCellCalibrated: false,
  gyroCalibrated: false,
  lastSample: null,
  invalidPackets: 0,
  lostPackets: 0,
};

type SampleListener = (samples: SensorSample[]) => void;

interface DeviceState {
  bleAvailable: boolean;
  unavailableReason: string | null;
  state: BleConnectionState;
  discovered: DiscoveredDevice[];
  connected: DiscoveredDevice | null;
  info: DeviceInfo | null;
  health: SensorHealth;
  error: string | null;
  registeredDeviceId: string | null;
  startScan: () => Promise<void>;
  stopScan: () => void;
  connect: (device: DiscoveredDevice) => Promise<void>;
  disconnect: () => Promise<void>;
  sendCommand: (command: number) => Promise<void>;
  subscribeSamples: (listener: SampleListener) => () => void;
}

const DeviceContext = createContext<DeviceState | null>(null);

export function DeviceProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const ble = useRef<PhysioBandBleService | null>(null);
  if (ble.current === null) ble.current = new PhysioBandBleService();
  const service = ble.current;

  const [state, setState] = useState<BleConnectionState>(service.available ? 'idle' : 'unavailable');
  const [discovered, setDiscovered] = useState<DiscoveredDevice[]>([]);
  const [connected, setConnected] = useState<DiscoveredDevice | null>(null);
  const [info, setInfo] = useState<DeviceInfo | null>(null);
  const [health, setHealth] = useState<SensorHealth>(EMPTY_HEALTH);
  const [error, setError] = useState<string | null>(null);
  const [registeredDeviceId, setRegisteredDeviceId] = useState<string | null>(null);

  const deviceRef = useRef<Device | null>(null);
  const targetRef = useRef<DiscoveredDevice | null>(null);
  const manualDisconnect = useRef(false);
  const stopScanRef = useRef<(() => void) | null>(null);
  const subs = useRef<Subscription[]>([]);
  const listeners = useRef(new Set<SampleListener>());
  const lostHandler = useRef<() => Promise<void>>(async () => undefined);
  const stats = useRef({ packets: 0, samples: 0, invalid: 0, lost: 0, lastSeq: -1, lastStatus: 0, lastAt: 0, last: null as SensorSample | null });

  // Bluetooth adapter state
  useEffect(() => {
    const sub = service.onStateChange((s) => {
      if (s === 'PoweredOff') setState('bluetooth_off');
      else if (s === 'Unauthorized') setState('unauthorized');
      else if (s === 'PoweredOn') setState((prev) => (prev === 'bluetooth_off' || prev === 'unauthorized' ? 'idle' : prev));
    });
    return () => {
      sub?.remove();
      service.destroy();
    };
  }, [service]);

  // Publish sensor health at 4 Hz.
  useEffect(() => {
    let prev = { packets: 0, samples: 0, at: Date.now() };
    const timer = setInterval(() => {
      const s = stats.current;
      const now = Date.now();
      const dt = (now - prev.at) / 1000;
      const st = s.lastStatus;
      setHealth({
        receiving: now - s.lastAt < 1500,
        packetsPerSecond: Math.round((s.packets - prev.packets) / dt),
        samplesPerSecond: Math.round((s.samples - prev.samples) / dt),
        upperArmOk: (st & STATUS_BITS.UPPER_ARM_OK) !== 0,
        forearmOk: (st & STATUS_BITS.FOREARM_OK) !== 0,
        loadCellOk: (st & STATUS_BITS.LOAD_CELL_OK) !== 0,
        loadCellCalibrated: (st & STATUS_BITS.LOAD_CELL_CALIBRATED) !== 0,
        gyroCalibrated: (st & STATUS_BITS.GYRO_CALIBRATED) !== 0,
        lastSample: s.last,
        invalidPackets: s.invalid,
        lostPackets: s.lost,
      });
      prev = { packets: s.packets, samples: s.samples, at: now };
    }, 250);
    return () => clearInterval(timer);
  }, []);

  const clearSubs = () => {
    subs.current.forEach((s) => s.remove());
    subs.current = [];
  };

  const handlePacket = useCallback((b64: string) => {
    const s = stats.current;
    try {
      const packet = decodeBase64Packet(b64);
      if (s.lastSeq >= 0) {
        const gap = (packet.sequence - s.lastSeq + 65536) % 65536;
        if (gap > 1 && gap < 1000) s.lost += gap - 1;
      }
      s.lastSeq = packet.sequence;
      s.packets += 1;
      s.samples += packet.samples.length;
      s.lastAt = Date.now();
      s.last = packet.samples[packet.samples.length - 1];
      s.lastStatus = s.last.status;
      listeners.current.forEach((l) => l(packet.samples));
    } catch (e) {
      if (e instanceof PacketError) s.invalid += 1;
    }
  }, []);

  const registerWithBackend = useCallback(
    async (target: DiscoveredDevice, deviceInfo: DeviceInfo | null) => {
      if (!user) return;
      const deviceId = deviceInfo?.device_id ?? `PB-${target.id.replace(/[^A-Za-z0-9]/g, '').slice(-8)}`;
      try {
        await deviceApi.register({
          device_id: deviceId,
          device_name: target.name,
          firmware_version: deviceInfo?.firmware ?? 'unknown',
          protocol_version: deviceInfo?.protocol ?? 1,
          ble_address: target.id,
          sample_rate_hz: deviceInfo?.sample_rate_hz,
        });
        setRegisteredDeviceId(deviceId);
      } catch {
        setRegisteredDeviceId(null); // workouts can still start without a linked device
      }
    },
    [user],
  );

  const establish = useCallback(
    async (target: DiscoveredDevice) => {
      const { device, info: deviceInfo } = await service.connect(target.id);
      deviceRef.current = device;
      stats.current = { packets: 0, samples: 0, invalid: 0, lost: 0, lastSeq: -1, lastStatus: 0, lastAt: 0, last: null };
      setInfo(deviceInfo);
      setConnected(target);
      clearSubs();
      subs.current.push(service.monitor(device, handlePacket, (msg) => setError(msg)));
      const dsub = service.onDisconnected(target.id, () => void lostHandler.current());
      if (dsub) subs.current.push(dsub);
      await service.sendCommand(device, COMMANDS.START_STREAM);
      setState('connected');
      setError(null);
      await secureStorage.setLastDevice({ id: target.id, name: target.name });
      void registerWithBackend(target, deviceInfo);
    },
    [service, handlePacket, registerWithBackend],
  );

  const onLostConnection = useCallback(async () => {
    clearSubs();
    deviceRef.current = null;
    if (manualDisconnect.current || !targetRef.current) {
      setState('disconnected');
      setConnected(null);
      return;
    }
    // Automatic reconnection after an unexpected BLE drop.
    setState('reconnecting');
    for (let attempt = 1; attempt <= RECONNECT.ATTEMPTS; attempt++) {
      await new Promise((r) => setTimeout(r, RECONNECT.DELAY_MS));
      if (manualDisconnect.current || !targetRef.current) return;
      try {
        await establish(targetRef.current);
        return;
      } catch {
        setError(`Reconnect attempt ${attempt} of ${RECONNECT.ATTEMPTS} failed`);
      }
    }
    setState('disconnected');
    setConnected(null);
    setError('Connection lost. Move closer to the device and connect again.');
  }, [establish]);
  lostHandler.current = onLostConnection;

  const stopScan = useCallback(() => {
    stopScanRef.current?.();
    stopScanRef.current = null;
    setState((prev) => (prev === 'scanning' ? 'idle' : prev));
  }, []);

  const startScan = useCallback(async () => {
    if (!service.available) return;
    setError(null);
    const granted = await service.requestPermissions();
    if (!granted) {
      setState('unauthorized');
      setError('Bluetooth permission is required to find the PhysioBand device.');
      return;
    }
    setDiscovered([]);
    setState('scanning');
    stopScanRef.current = service.scan(
      (d) => setDiscovered((list) => (list.some((x) => x.id === d.id) ? list : [...list, d])),
      (msg) => {
        setError(msg);
        setState('idle');
      },
    );
    setTimeout(() => stopScan(), BLE.SCAN_TIMEOUT_MS);
  }, [service, stopScan]);

  const connect = useCallback(
    async (target: DiscoveredDevice) => {
      stopScan();
      manualDisconnect.current = false;
      targetRef.current = target;
      setState('connecting');
      setError(null);
      try {
        await establish(target);
      } catch (e) {
        targetRef.current = null;
        setState('idle');
        setError(e instanceof Error ? e.message : 'Could not connect');
        throw e;
      }
    },
    [establish, stopScan],
  );

  const disconnect = useCallback(async () => {
    manualDisconnect.current = true;
    const device = deviceRef.current;
    const target = targetRef.current;
    targetRef.current = null;
    if (device) {
      try {
        await service.sendCommand(device, COMMANDS.STOP_STREAM);
      } catch {
        // ignore - disconnecting anyway
      }
    }
    if (target) await service.disconnect(target.id);
    clearSubs();
    deviceRef.current = null;
    setConnected(null);
    setInfo(null);
    setState('idle');
  }, [service]);

  const sendCommand = useCallback(
    async (command: number) => {
      if (!deviceRef.current) throw new Error('No device connected');
      await service.sendCommand(deviceRef.current, command);
    },
    [service],
  );

  const subscribeSamples = useCallback((listener: SampleListener) => {
    listeners.current.add(listener);
    return () => {
      listeners.current.delete(listener);
    };
  }, []);

  // Disconnect when the user logs out.
  useEffect(() => {
    if (!user && targetRef.current) void disconnect();
  }, [user, disconnect]);

  const value = useMemo<DeviceState>(
    () => ({
      bleAvailable: service.available,
      unavailableReason: service.unavailableReason,
      state,
      discovered,
      connected,
      info,
      health,
      error,
      registeredDeviceId,
      startScan,
      stopScan,
      connect,
      disconnect,
      sendCommand,
      subscribeSamples,
    }),
    [service, state, discovered, connected, info, health, error, registeredDeviceId, startScan, stopScan, connect, disconnect, sendCommand, subscribeSamples],
  );

  return <DeviceContext.Provider value={value}>{children}</DeviceContext.Provider>;
}

export function useDevice(): DeviceState {
  const ctx = useContext(DeviceContext);
  if (!ctx) throw new Error('useDevice must be used inside DeviceProvider');
  return ctx;
}
