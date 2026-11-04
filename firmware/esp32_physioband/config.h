// =============================================================================
// PhysioBand AI - ESP32 firmware configuration
// All pins, sensor settings, BLE UUIDs and protocol constants live here.
// The BLE UUIDs and packet layout MUST match frontend/src/constants/ble.ts.
// =============================================================================
#pragma once

#define FIRMWARE_VERSION "1.0.0"
#define PROTOCOL_VERSION 1

// ---------------------------------------------------------------------------
// I2C bus shared by both MPU6050 (GY-521) modules
// ---------------------------------------------------------------------------
#define PIN_I2C_SDA 21
#define PIN_I2C_SCL 22
#define I2C_CLOCK_HZ 400000UL

// AD0 pin LOW (to GND)  -> address 0x68 -> UPPER-ARM sensor
// AD0 pin HIGH (to 3V3) -> address 0x69 -> FOREARM sensor
#define MPU_ADDR_UPPER_ARM 0x68
#define MPU_ADDR_FOREARM 0x69

// MPU6050 ranges: +/-8 g (4096 LSB/g) and +/-1000 deg/s (32.8 LSB/(deg/s)).
// A strong band curl can exceed +/-4 g / +/-500 deg/s briefly, so wider ranges are used.
#define MPU_ACCEL_CONFIG 0x10
#define MPU_GYRO_CONFIG 0x10
#define MPU_ACCEL_LSB_PER_G 4096.0f
#define MPU_GYRO_LSB_PER_DPS 32.8f
#define MPU_DLPF_CONFIG 0x03  // on-chip low-pass ~44 Hz (anti-aliasing for 50 Hz sampling)

// ---------------------------------------------------------------------------
// HX711 load-cell amplifier (any free GPIO works; avoid strapping pins 0, 2, 12, 15)
// ---------------------------------------------------------------------------
#define PIN_HX711_DT 16   // HX711 DOUT / DT
#define PIN_HX711_SCK 4   // HX711 PD_SCK / SCK

// Raw HX711 counts per kilogram. THIS VALUE IS HARDWARE SPECIFIC and must be found
// with the "cal <kg>" serial command using a known weight. The calibrated value is
// saved in flash (NVS) and overrides this default.
#define HX711_DEFAULT_CALIBRATION_FACTOR 21000.0f
#define HX711_STALE_MS 500  // load cell reported as faulty if no new reading for this long
#define GRAVITY_MS2 9.80665f

// ---------------------------------------------------------------------------
// Sampling and packets
// ---------------------------------------------------------------------------
#define SAMPLE_RATE_HZ 50
#define SAMPLE_PERIOD_US (1000000UL / SAMPLE_RATE_HZ)
#define MAX_SAMPLES_PER_PACKET 4          // 8 + 4*33 = 140 byte notification (needs MTU >= 143)
#define PACKET_HEADER_SIZE 8
#define PACKET_SAMPLE_SIZE 33
#define BLE_PREFERRED_MTU 247

// Sensor status flag bits (sent with every sample)
#define STATUS_UPPER_ARM_OK (1 << 0)
#define STATUS_FOREARM_OK (1 << 1)
#define STATUS_LOAD_CELL_OK (1 << 2)
#define STATUS_LOAD_CELL_CALIBRATED (1 << 3)
#define STATUS_GYRO_CALIBRATED (1 << 4)

// ---------------------------------------------------------------------------
// BLE GATT definition
// ---------------------------------------------------------------------------
#define BLE_DEVICE_NAME_PREFIX "PhysioBand-"
#define BLE_SERVICE_UUID "7b1e0001-5c3a-4d8e-9f21-6a0b3c4d5e6f"
#define BLE_CHAR_SENSOR_DATA_UUID "7b1e0002-5c3a-4d8e-9f21-6a0b3c4d5e6f"  // notify: sensor packets
#define BLE_CHAR_CONTROL_UUID "7b1e0003-5c3a-4d8e-9f21-6a0b3c4d5e6f"      // write: 1-byte commands
#define BLE_CHAR_DEVICE_INFO_UUID "7b1e0004-5c3a-4d8e-9f21-6a0b3c4d5e6f"  // read: JSON device info

// Control commands written by the mobile app
#define CMD_START_STREAM 0x01
#define CMD_STOP_STREAM 0x02
#define CMD_TARE_LOAD_CELL 0x03
#define CMD_CALIBRATE_GYRO 0x04

#define SERIAL_BAUD 115200
