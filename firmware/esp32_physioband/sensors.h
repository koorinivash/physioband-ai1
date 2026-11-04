// =============================================================================
// Sensor drivers: 2 x MPU6050 (direct register access over I2C) + HX711 load cell.
// =============================================================================
#pragma once

#include <Arduino.h>
#include <HX711.h>        // "HX711 Arduino Library" by Bogdan Necula (bogde)
#include <Preferences.h>  // ESP32 NVS flash storage for calibration values
#include <Wire.h>

#include "config.h"

// MPU6050 registers
#define MPU_REG_SMPLRT_DIV 0x19
#define MPU_REG_CONFIG 0x1A
#define MPU_REG_GYRO_CONFIG 0x1B
#define MPU_REG_ACCEL_CONFIG 0x1C
#define MPU_REG_ACCEL_XOUT_H 0x3B
#define MPU_REG_PWR_MGMT_1 0x6B
#define MPU_REG_WHO_AM_I 0x75

struct ImuReading {
  float ax, ay, az;  // g
  float gx, gy, gz;  // deg/s (gyro bias removed)
  bool ok;
};

class Mpu6050 {
 public:
  Mpu6050(uint8_t address, const char* name) : addr_(address), name_(name) {}

  bool begin() {
    uint8_t who = 0;
    if (!readRegs(MPU_REG_WHO_AM_I, &who, 1)) {
      Serial.printf("[IMU] %s (0x%02X) NOT FOUND - check wiring and AD0 level\n", name_, addr_);
      present_ = false;
      return false;
    }
    // Genuine parts return 0x68; some clones return 0x70/0x72/0x98 but still work.
    if (who != 0x68) Serial.printf("[IMU] %s WHO_AM_I=0x%02X (clone chip?) - continuing\n", name_, who);
    present_ = writeReg(MPU_REG_PWR_MGMT_1, 0x01) &&            // wake up, PLL with X gyro clock
               writeReg(MPU_REG_SMPLRT_DIV, 0x04) &&            // 1 kHz / (1+4) = 200 Hz internal rate
               writeReg(MPU_REG_CONFIG, MPU_DLPF_CONFIG) &&     // digital low-pass filter
               writeReg(MPU_REG_GYRO_CONFIG, MPU_GYRO_CONFIG) &&
               writeReg(MPU_REG_ACCEL_CONFIG, MPU_ACCEL_CONFIG);
    delay(50);
    Serial.printf("[IMU] %s at 0x%02X %s\n", name_, addr_, present_ ? "OK" : "CONFIG FAILED");
    return present_;
  }

  ImuReading read() {
    ImuReading r{};
    uint8_t buf[14];
    if (!present_ || !readRegs(MPU_REG_ACCEL_XOUT_H, buf, 14)) {
      r.ok = false;
      if (present_ && ++failures_ > 25) {  // ~0.5 s of failures -> try to re-initialise
        failures_ = 0;
        begin();
      }
      return r;
    }
    failures_ = 0;
    int16_t raw[7];
    for (int i = 0; i < 7; i++) raw[i] = (int16_t)((buf[2 * i] << 8) | buf[2 * i + 1]);
    r.ax = raw[0] / MPU_ACCEL_LSB_PER_G;
    r.ay = raw[1] / MPU_ACCEL_LSB_PER_G;
    r.az = raw[2] / MPU_ACCEL_LSB_PER_G;
    // raw[3] is the temperature sensor (unused)
    r.gx = raw[4] / MPU_GYRO_LSB_PER_DPS - bias_[0];
    r.gy = raw[5] / MPU_GYRO_LSB_PER_DPS - bias_[1];
    r.gz = raw[6] / MPU_GYRO_LSB_PER_DPS - bias_[2];
    r.ok = true;
    return r;
  }

  void setBias(float bx, float by, float bz) { bias_[0] = bx; bias_[1] = by; bias_[2] = bz; }
  const float* bias() const { return bias_; }
  bool present() const { return present_; }
  const char* name() const { return name_; }

 private:
  bool writeReg(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(addr_);
    Wire.write(reg);
    Wire.write(value);
    return Wire.endTransmission() == 0;
  }

  bool readRegs(uint8_t reg, uint8_t* out, size_t len) {
    Wire.beginTransmission(addr_);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom((int)addr_, (int)len) != (int)len) return false;
    for (size_t i = 0; i < len; i++) out[i] = Wire.read();
    return true;
  }

  uint8_t addr_;
  const char* name_;
  bool present_ = false;
  uint8_t failures_ = 0;
  float bias_[3] = {0, 0, 0};
};

// -----------------------------------------------------------------------------
// HX711 + S-type load cell. Reads are non-blocking: the HX711 produces 10 SPS
// (RATE pin low, most GY/HX711 boards) or 80 SPS (RATE pin high); the latest
// value is held between conversions and sent with every 50 Hz sample.
// -----------------------------------------------------------------------------
class LoadCell {
 public:
  void begin(Preferences& prefs) {
    prefs_ = &prefs;
    hx_.begin(PIN_HX711_DT, PIN_HX711_SCK);
    factor_ = prefs.getFloat("lc_factor", HX711_DEFAULT_CALIBRATION_FACTOR);
    offset_ = prefs.getLong("lc_offset", 0);
    calibrated_ = prefs.isKey("lc_factor");
    unsigned long start = millis();
    while (!hx_.is_ready() && millis() - start < 1000) delay(10);
    present_ = hx_.is_ready();
    Serial.printf("[HX711] %s, factor=%.2f counts/kg (%s), offset=%ld\n", present_ ? "OK" : "NOT RESPONDING",
                  factor_, calibrated_ ? "calibrated" : "DEFAULT - run 'cal <kg>'", (long)offset_);
    if (present_ && !prefs.isKey("lc_offset")) tare();  // first boot: zero with no load
  }

  // Call often; picks up a new conversion when one is ready.
  void update() {
    if (hx_.is_ready()) {
      lastRaw_ = hx_.read();
      lastReadMs_ = millis();
      present_ = true;
    }
  }

  float forceN() const { return ((float)(lastRaw_ - offset_) / factor_) * GRAVITY_MS2; }
  bool ok() const { return present_ && (millis() - lastReadMs_) < HX711_STALE_MS; }
  bool calibrated() const { return calibrated_; }
  long raw() const { return lastRaw_; }
  float factor() const { return factor_; }

  long averageRaw(uint8_t samples) {
    long long sum = 0;
    uint8_t got = 0;
    unsigned long start = millis();
    while (got < samples && millis() - start < 5000) {
      if (hx_.is_ready()) { sum += hx_.read(); got++; }
      delay(5);
    }
    return got ? (long)(sum / got) : lastRaw_;
  }

  // Zero the load cell with the band attached but slack.
  void tare() {
    offset_ = averageRaw(15);
    prefs_->putLong("lc_offset", offset_);
    Serial.printf("[HX711] Tare done, offset=%ld\n", (long)offset_);
  }

  // Hang a known mass (kg) from the load cell, then call this.
  bool calibrate(float knownKg) {
    if (knownKg <= 0) return false;
    long raw = averageRaw(20);
    float f = (float)(raw - offset_) / knownKg;
    if (fabsf(f) < 1.0f) {
      Serial.println("[HX711] Calibration failed: reading did not change. Is the weight attached?");
      return false;
    }
    setFactor(f);
    return true;
  }

  void setFactor(float f) {
    factor_ = f;
    calibrated_ = true;
    prefs_->putFloat("lc_factor", factor_);
    Serial.printf("[HX711] Calibration factor set to %.2f counts/kg (saved)\n", factor_);
  }

 private:
  HX711 hx_;
  Preferences* prefs_ = nullptr;
  float factor_ = HX711_DEFAULT_CALIBRATION_FACTOR;
  long offset_ = 0;
  long lastRaw_ = 0;
  unsigned long lastReadMs_ = 0;
  bool present_ = false;
  bool calibrated_ = false;
};
