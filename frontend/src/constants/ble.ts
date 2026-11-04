/**
 * BLE protocol shared with the ESP32 firmware.
 * MUST match firmware/esp32_physioband/config.h and ble_service.h.
 */
export const BLE = {
  DEVICE_NAME_PREFIX: 'PhysioBand-',
  SERVICE_UUID: '7b1e0001-5c3a-4d8e-9f21-6a0b3c4d5e6f',
  SENSOR_DATA_UUID: '7b1e0002-5c3a-4d8e-9f21-6a0b3c4d5e6f',
  CONTROL_UUID: '7b1e0003-5c3a-4d8e-9f21-6a0b3c4d5e6f',
  DEVICE_INFO_UUID: '7b1e0004-5c3a-4d8e-9f21-6a0b3c4d5e6f',
  REQUESTED_MTU: 185,
  SCAN_TIMEOUT_MS: 12000,
};

export const PROTOCOL = {
  VERSION: 1,
  HEADER_SIZE: 8,
  SAMPLE_SIZE: 33,
  MAX_SAMPLES_PER_PACKET: 4,
  SAMPLE_RATE_HZ: 50,
  ACCEL_SCALE: 1000, // int16 milli-g -> g
  GYRO_SCALE: 10, // int16 0.1 deg/s -> deg/s
  FORCE_SCALE: 100, // int32 0.01 N -> N
};

export const COMMANDS = {
  START_STREAM: 0x01,
  STOP_STREAM: 0x02,
  TARE_LOAD_CELL: 0x03,
  CALIBRATE_GYRO: 0x04,
};

export const STATUS_BITS = {
  UPPER_ARM_OK: 1 << 0,
  FOREARM_OK: 1 << 1,
  LOAD_CELL_OK: 1 << 2,
  LOAD_CELL_CALIBRATED: 1 << 3,
  GYRO_CALIBRATED: 1 << 4,
};
