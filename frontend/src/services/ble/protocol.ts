/**
 * Decoder for the PhysioBand BLE sensor packet (protocol v1, little-endian).
 * Layout documented in firmware/esp32_physioband/ble_service.h:
 *   header : u8 version | u8 sample_count | u16 seq | u32 device_id
 *   sample : u32 timestamp_ms | i16 x6 upper arm | i16 x6 forearm | i32 force (0.01 N) | u8 status
 */
import { PROTOCOL, STATUS_BITS } from '../../constants/ble';
import type { SensorSample } from '../../types/api';
import type { DecodedPacket } from '../../types/ble';

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const LOOKUP = new Uint8Array(256).fill(255);
for (let i = 0; i < B64.length; i++) LOOKUP[B64.charCodeAt(i)] = i;

/** react-native-ble-plx delivers characteristic values as base64 strings. */
export function base64ToBytes(b64: string): Uint8Array {
  const clean = b64.replace(/[^A-Za-z0-9+/]/g, '');
  const out = new Uint8Array(Math.floor((clean.length * 3) / 4));
  let buffer = 0;
  let bits = 0;
  let o = 0;
  for (let i = 0; i < clean.length; i++) {
    buffer = (buffer << 6) | LOOKUP[clean.charCodeAt(i)];
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      out[o++] = (buffer >> bits) & 0xff;
    }
  }
  return out.subarray(0, o);
}

export function bytesToBase64(bytes: Uint8Array): string {
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const n = (bytes[i] << 16) | ((bytes[i + 1] ?? 0) << 8) | (bytes[i + 2] ?? 0);
    out += B64[(n >> 18) & 63] + B64[(n >> 12) & 63];
    out += i + 1 < bytes.length ? B64[(n >> 6) & 63] : '=';
    out += i + 2 < bytes.length ? B64[n & 63] : '=';
  }
  return out;
}

/** The device-info characteristic is plain ASCII JSON. */
export function bytesToAscii(bytes: Uint8Array): string {
  let s = '';
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return s;
}

export class PacketError extends Error {}

const round = (v: number, d: number) => Math.round(v * 10 ** d) / 10 ** d;

export function decodePacket(bytes: Uint8Array): DecodedPacket {
  if (bytes.length < PROTOCOL.HEADER_SIZE) throw new PacketError(`Packet too short (${bytes.length} bytes)`);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const version = view.getUint8(0);
  if (version !== PROTOCOL.VERSION) throw new PacketError(`Unsupported protocol version ${version}`);
  const count = view.getUint8(1);
  const expected = PROTOCOL.HEADER_SIZE + count * PROTOCOL.SAMPLE_SIZE;
  if (count < 1 || count > PROTOCOL.MAX_SAMPLES_PER_PACKET || bytes.length < expected) {
    throw new PacketError(`Invalid packet: ${count} samples in ${bytes.length} bytes (MTU too small?)`);
  }

  const samples: SensorSample[] = [];
  for (let i = 0; i < count; i++) {
    const o = PROTOCOL.HEADER_SIZE + i * PROTOCOL.SAMPLE_SIZE;
    const status = view.getUint8(o + 32);
    const imu = (base: number, ok: boolean) => {
      if (!ok) return [null, null, null, null, null, null];
      const v: number[] = [];
      for (let k = 0; k < 3; k++) v.push(round(view.getInt16(base + 2 * k, true) / PROTOCOL.ACCEL_SCALE, 3));
      for (let k = 3; k < 6; k++) v.push(round(view.getInt16(base + 2 * k, true) / PROTOCOL.GYRO_SCALE, 1));
      return v;
    };
    samples.push({
      timestamp_ms: view.getUint32(o, true),
      ua: imu(o + 4, (status & STATUS_BITS.UPPER_ARM_OK) !== 0),
      fa: imu(o + 16, (status & STATUS_BITS.FOREARM_OK) !== 0),
      force_n: status & STATUS_BITS.LOAD_CELL_OK ? round(view.getInt32(o + 28, true) / PROTOCOL.FORCE_SCALE, 2) : null,
      status,
    });
  }
  return { version, sequence: view.getUint16(2, true), deviceId: view.getUint32(4, true), samples };
}

export function decodeBase64Packet(b64: string): DecodedPacket {
  return decodePacket(base64ToBytes(b64));
}

/** Validation used before uploading: drops samples with no usable sensor at all. */
export function isUsableSample(s: SensorSample): boolean {
  return s.ua[0] !== null || s.fa[0] !== null || s.force_n !== null;
}
