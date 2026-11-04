// =============================================================================
// PhysioBand AI - ESP32 DevKit V1 firmware
//
// Reads two MPU6050 IMUs (upper arm 0x68, forearm 0x69) and an S-type load cell
// through an HX711 at a fixed 50 Hz, timestamps every sample and streams it to
// the mobile app over BLE notifications (see ble_service.h for the packet format).
//
// Libraries: ESP32 Arduino core (BLE, Wire, Preferences) + "HX711" by Bogdan Necula.
//
// Serial commands (115200 baud, newline terminated):
//   help            list commands
//   status          sensor / BLE status
//   read            print one sample in physical units
//   tare            zero the load cell (band slack)
//   cal <kg>        calibrate with a known mass hanging from the load cell
//   factor <value>  set the HX711 calibration factor directly (counts/kg)
//   gyrocal         estimate gyro bias (keep both sensors still for 3 s)
//   csv on|off      stream CSV lines for ml/scripts/collect_data.py
//   debug on|off    print a status line every 2 s
// =============================================================================
#include <Preferences.h>
#include <Wire.h>

#include "ble_service.h"
#include "config.h"
#include "sensors.h"

Mpu6050 upperArm(MPU_ADDR_UPPER_ARM, "upper-arm");
Mpu6050 forearm(MPU_ADDR_FOREARM, "forearm");
LoadCell loadCell;
PhysioBandBle ble;
Preferences prefs;

uint32_t deviceId = 0;
String deviceIdText;
bool csvMode = false;
bool debugMode = false;
bool gyroCalibrated = false;
volatile uint8_t pendingCommand = 0;  // BLE commands are executed in loop(), not in the BLE callback
unsigned long nextSampleUs = 0;
unsigned long lastDebugMs = 0;
uint32_t samplesTaken = 0;
uint32_t lateSamples = 0;

void onBleCommand(uint8_t cmd) {
  if (cmd == CMD_TARE_LOAD_CELL || cmd == CMD_CALIBRATE_GYRO) pendingCommand = cmd;
}

void loadGyroBias() {
  gyroCalibrated = prefs.isKey("ua_bx");
  upperArm.setBias(prefs.getFloat("ua_bx", 0), prefs.getFloat("ua_by", 0), prefs.getFloat("ua_bz", 0));
  forearm.setBias(prefs.getFloat("fa_bx", 0), prefs.getFloat("fa_by", 0), prefs.getFloat("fa_bz", 0));
}

// Average the gyro output while still; the mean is the bias that is subtracted later.
void calibrateGyro() {
  Serial.println("[CAL] Keep both sensors completely still...");
  upperArm.setBias(0, 0, 0);
  forearm.setBias(0, 0, 0);
  double sum[6] = {0};
  int n = 0;
  for (int i = 0; i < 150; i++) {
    ImuReading a = upperArm.read(), b = forearm.read();
    if (a.ok && b.ok) {
      sum[0] += a.gx; sum[1] += a.gy; sum[2] += a.gz;
      sum[3] += b.gx; sum[4] += b.gy; sum[5] += b.gz;
      n++;
    }
    delay(20);
  }
  if (n < 50) {
    Serial.println("[CAL] Gyro calibration failed: IMU readings unavailable");
    loadGyroBias();
    return;
  }
  const char* keys[6] = {"ua_bx", "ua_by", "ua_bz", "fa_bx", "fa_by", "fa_bz"};
  for (int i = 0; i < 6; i++) prefs.putFloat(keys[i], (float)(sum[i] / n));
  loadGyroBias();
  Serial.printf("[CAL] Gyro bias saved. UA=(%.2f, %.2f, %.2f) FA=(%.2f, %.2f, %.2f) deg/s\n", sum[0] / n, sum[1] / n,
                sum[2] / n, sum[3] / n, sum[4] / n, sum[5] / n);
}

SensorSample takeSample() {
  SensorSample s{};
  s.timestampMs = millis();
  ImuReading a = upperArm.read();
  ImuReading b = forearm.read();
  loadCell.update();
  s.ua[0] = a.ax; s.ua[1] = a.ay; s.ua[2] = a.az; s.ua[3] = a.gx; s.ua[4] = a.gy; s.ua[5] = a.gz;
  s.fa[0] = b.ax; s.fa[1] = b.ay; s.fa[2] = b.az; s.fa[3] = b.gx; s.fa[4] = b.gy; s.fa[5] = b.gz;
  s.forceN = loadCell.forceN();

  // Basic validation: a disconnected IMU on a pulled-up bus can return all zeros.
  bool aValid = a.ok && !(a.ax == 0 && a.ay == 0 && a.az == 0);
  bool bValid = b.ok && !(b.ax == 0 && b.ay == 0 && b.az == 0);
  s.status = (aValid ? STATUS_UPPER_ARM_OK : 0) | (bValid ? STATUS_FOREARM_OK : 0) |
             (loadCell.ok() ? STATUS_LOAD_CELL_OK : 0) | (loadCell.calibrated() ? STATUS_LOAD_CELL_CALIBRATED : 0) |
             (gyroCalibrated ? STATUS_GYRO_CALIBRATED : 0);
  return s;
}

void printSample(const SensorSample& s) {
  Serial.printf("t=%lu ms | UA a=(%.3f, %.3f, %.3f) g  g=(%.1f, %.1f, %.1f) dps | ", (unsigned long)s.timestampMs,
                s.ua[0], s.ua[1], s.ua[2], s.ua[3], s.ua[4], s.ua[5]);
  Serial.printf("FA a=(%.3f, %.3f, %.3f) g  g=(%.1f, %.1f, %.1f) dps | ", s.fa[0], s.fa[1], s.fa[2], s.fa[3], s.fa[4],
                s.fa[5]);
  Serial.printf("force=%.2f N (raw %ld) | status=0x%02X\n", s.forceN, loadCell.raw(), s.status);
}

void printCsv(const SensorSample& s) {
  Serial.printf("D,%lu,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%.3f,%u\n",
                (unsigned long)s.timestampMs, s.ua[0], s.ua[1], s.ua[2], s.ua[3], s.ua[4], s.ua[5], s.fa[0], s.fa[1],
                s.fa[2], s.fa[3], s.fa[4], s.fa[5], s.forceN, s.status);
}

void printStatus() {
  Serial.printf("Device %s  firmware %s  protocol v%d\n", deviceIdText.c_str(), FIRMWARE_VERSION, PROTOCOL_VERSION);
  Serial.printf("  Upper-arm IMU 0x%02X: %s   Forearm IMU 0x%02X: %s\n", MPU_ADDR_UPPER_ARM,
                upperArm.present() ? "present" : "MISSING", MPU_ADDR_FOREARM, forearm.present() ? "present" : "MISSING");
  Serial.printf("  Load cell: %s, %s (factor %.2f)\n", loadCell.ok() ? "OK" : "NO DATA",
                loadCell.calibrated() ? "calibrated" : "NOT calibrated", loadCell.factor());
  Serial.printf("  Gyro bias: %s\n", gyroCalibrated ? "calibrated" : "not calibrated (run gyrocal)");
  Serial.printf("  BLE: %s, %s, packets sent %lu\n", ble.connected() ? "connected" : "advertising",
                ble.streaming() ? "streaming" : "idle", (unsigned long)ble.sentPackets());
  Serial.printf("  Samples %lu, late %lu\n", (unsigned long)samplesTaken, (unsigned long)lateSamples);
}

void scanI2C() {
  Serial.print("[I2C] Devices found:");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) { Serial.printf(" 0x%02X", addr); found++; }
  }
  Serial.println(found ? "" : " none - check SDA/SCL wiring and power");
}

void handleSerial() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;
  if (line == "help") {
    Serial.println("Commands: status | read | tare | cal <kg> | factor <value> | gyrocal | csv on|off | debug on|off | i2c");
  } else if (line == "status") {
    printStatus();
  } else if (line == "read") {
    printSample(takeSample());
  } else if (line == "tare") {
    loadCell.tare();
  } else if (line.startsWith("cal ")) {
    float kg = line.substring(4).toFloat();
    if (!loadCell.calibrate(kg)) Serial.println("Usage: cal <known mass in kg>, e.g. cal 2.0");
  } else if (line.startsWith("factor ")) {
    float f = line.substring(7).toFloat();
    if (f != 0) loadCell.setFactor(f);
  } else if (line == "gyrocal") {
    calibrateGyro();
  } else if (line == "csv on") {
    csvMode = true;
  } else if (line == "csv off") {
    csvMode = false;
    Serial.println("CSV streaming off");
  } else if (line == "debug on") {
    debugMode = true;
  } else if (line == "debug off") {
    debugMode = false;
  } else if (line == "i2c") {
    scanI2C();
  } else {
    Serial.printf("Unknown command '%s' (type help)\n", line.c_str());
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(300);
  Serial.println("\n=== PhysioBand AI firmware " FIRMWARE_VERSION " ===");

  uint64_t mac = ESP.getEfuseMac();
  deviceId = (uint32_t)(mac >> 16);  // unique per chip
  char idText[16];
  snprintf(idText, sizeof(idText), "PB-%08lX", (unsigned long)deviceId);
  deviceIdText = idText;
  String bleName = String(BLE_DEVICE_NAME_PREFIX) + deviceIdText.substring(deviceIdText.length() - 4);

  prefs.begin("physioband", false);
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_CLOCK_HZ);
  scanI2C();
  upperArm.begin();
  forearm.begin();
  loadGyroBias();
  loadCell.begin(prefs);

  ble.begin(bleName, deviceId, deviceIdText, onBleCommand);
  printStatus();
  Serial.println("Type 'help' for serial commands.");
  nextSampleUs = micros();
}

void loop() {
  handleSerial();
  ble.service();
  loadCell.update();

  if (pendingCommand) {
    uint8_t cmd = pendingCommand;
    pendingCommand = 0;
    if (cmd == CMD_TARE_LOAD_CELL) loadCell.tare();
    if (cmd == CMD_CALIBRATE_GYRO) calibrateGyro();
    nextSampleUs = micros();
  }

  // Fixed-rate sampling scheduler (50 Hz). If the loop falls behind, skip ahead
  // instead of bursting, so timestamps stay evenly spaced.
  unsigned long now = micros();
  if ((long)(now - nextSampleUs) >= 0) {
    nextSampleUs += SAMPLE_PERIOD_US;
    if ((long)(now - nextSampleUs) > (long)SAMPLE_PERIOD_US) {
      nextSampleUs = now + SAMPLE_PERIOD_US;
      lateSamples++;
    }
    SensorSample s = takeSample();
    samplesTaken++;
    ble.push(s);
    if (csvMode) printCsv(s);
  }

  if (debugMode && millis() - lastDebugMs > 2000) {
    lastDebugMs = millis();
    printSample(takeSample());
  }
}
