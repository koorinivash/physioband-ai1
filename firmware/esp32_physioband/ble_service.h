// =============================================================================
// BLE GATT server (ESP32 built-in Bluetooth Low Energy, Arduino "BLE" library).
//
// Service 7b1e0001-...  PhysioBand sensor service
//   7b1e0002-...  SENSOR_DATA  notify  binary packet (layout below)
//   7b1e0003-...  CONTROL      write   1-byte command (config.h CMD_*)
//   7b1e0004-...  DEVICE_INFO  read    JSON: device id, firmware, protocol, rates
//
// SENSOR_DATA packet, protocol v1, little-endian:
//   offset size type    field
//   0      1    uint8   protocol_version (=1)
//   1      1    uint8   sample_count N (1..4)
//   2      2    uint16  packet_seq (wraps at 65535)
//   4      4    uint32  device_id (lower 32 bits of the ESP32 MAC)
//   8+33*i per sample:
//     +0   4    uint32  timestamp_ms (millis())
//     +4   12   int16x6 upper arm: ax ay az (mg)  gx gy gz (0.1 deg/s)
//     +16  12   int16x6 forearm:   ax ay az (mg)  gx gy gz (0.1 deg/s)
//     +28  4    int32   force (0.01 N)
//     +32  1    uint8   status flags (config.h STATUS_*)
// =============================================================================
#pragma once

#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

#include "config.h"

struct SensorSample {
  uint32_t timestampMs;
  float ua[6];
  float fa[6];
  float forceN;
  uint8_t status;
};

typedef void (*CommandHandler)(uint8_t command);

class PhysioBandBle;
static PhysioBandBle* g_ble = nullptr;

class PhysioBandBle : public BLEServerCallbacks, public BLECharacteristicCallbacks {
 public:
  void begin(const String& deviceName, uint32_t deviceId, const String& deviceIdText, CommandHandler handler) {
    g_ble = this;
    deviceId_ = deviceId;
    handler_ = handler;

    BLEDevice::init(deviceName.c_str());
    BLEDevice::setMTU(BLE_PREFERRED_MTU);
    server_ = BLEDevice::createServer();
    server_->setCallbacks(this);

    BLEService* service = server_->createService(BLE_SERVICE_UUID);

    dataChar_ = service->createCharacteristic(BLE_CHAR_SENSOR_DATA_UUID,
                                              BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ);
    dataChar_->addDescriptor(new BLE2902());  // client characteristic configuration (enables notifications)

    BLECharacteristic* control = service->createCharacteristic(
        BLE_CHAR_CONTROL_UUID, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
    control->setCallbacks(this);

    BLECharacteristic* info = service->createCharacteristic(BLE_CHAR_DEVICE_INFO_UUID, BLECharacteristic::PROPERTY_READ);
    char json[200];
    snprintf(json, sizeof(json),
             "{\"device_id\":\"%s\",\"name\":\"%s\",\"firmware\":\"%s\",\"protocol\":%d,"
             "\"sample_rate_hz\":%d,\"max_samples_per_packet\":%d}",
             deviceIdText.c_str(), deviceName.c_str(), FIRMWARE_VERSION, PROTOCOL_VERSION, SAMPLE_RATE_HZ,
             MAX_SAMPLES_PER_PACKET);
    info->setValue((uint8_t*)json, strlen(json));

    service->start();
    BLEAdvertising* adv = BLEDevice::getAdvertising();
    adv->addServiceUUID(BLE_SERVICE_UUID);  // lets the app scan by service UUID
    adv->setScanResponse(true);
    adv->setMinPreferred(0x06);
    adv->setMaxPreferred(0x12);
    BLEDevice::startAdvertising();
    Serial.printf("[BLE] Advertising as '%s'\n", deviceName.c_str());
  }

  // --- BLEServerCallbacks ---
  void onConnect(BLEServer* server, esp_ble_gatts_cb_param_t* param) override {
    connected_ = true;
    connId_ = param->connect.conn_id;
    Serial.println("[BLE] Client connected");
  }

  void onDisconnect(BLEServer* server) override {
    connected_ = false;
    streaming_ = false;
    restartAdvertising_ = true;  // re-advertise from loop() so the app can reconnect
    Serial.println("[BLE] Client disconnected - streaming stopped");
  }

  // --- BLECharacteristicCallbacks (CONTROL characteristic) ---
  void onWrite(BLECharacteristic* c) override {
    if (c->getLength() < 1) return;
    uint8_t cmd = c->getData()[0];
    if (cmd == CMD_START_STREAM) {
      streaming_ = true;
      Serial.println("[BLE] Streaming started");
    } else if (cmd == CMD_STOP_STREAM) {
      streaming_ = false;
      Serial.println("[BLE] Streaming stopped");
    }
    if (handler_) handler_(cmd);
  }

  // Called from loop(): restart advertising after a disconnect.
  void service() {
    if (restartAdvertising_) {
      restartAdvertising_ = false;
      delay(200);
      BLEDevice::startAdvertising();
      Serial.println("[BLE] Advertising restarted");
    }
  }

  // Number of samples that fit the negotiated MTU (ATT payload = MTU - 3).
  uint8_t samplesPerPacket() {
    uint16_t mtu = server_ ? server_->getPeerMTU(connId_) : 23;
    int fit = ((int)mtu - 3 - PACKET_HEADER_SIZE) / PACKET_SAMPLE_SIZE;
    if (fit < 1) fit = 1;  // MTU 23 truncates packets; the app requests a larger MTU on connect
    return (uint8_t)min(fit, MAX_SAMPLES_PER_PACKET);
  }

  // Queue a sample; sends a notification once enough samples are buffered.
  void push(const SensorSample& s) {
    if (!connected_ || !streaming_) { count_ = 0; return; }
    encodeSample(&packet_[PACKET_HEADER_SIZE + count_ * PACKET_SAMPLE_SIZE], s);
    count_++;
    if (count_ >= samplesPerPacket()) flush();
  }

  bool connected() const { return connected_; }
  bool streaming() const { return streaming_; }
  uint32_t sentPackets() const { return sentPackets_; }

 private:
  static void put16(uint8_t* p, int16_t v) { p[0] = v & 0xFF; p[1] = (v >> 8) & 0xFF; }
  static void put32(uint8_t* p, uint32_t v) { for (int i = 0; i < 4; i++) p[i] = (v >> (8 * i)) & 0xFF; }

  static int16_t clamp16(float v) {
    long r = lroundf(v);
    return (int16_t)constrain(r, -32768L, 32767L);
  }

  static void encodeSample(uint8_t* p, const SensorSample& s) {
    put32(p, s.timestampMs);
    for (int i = 0; i < 3; i++) put16(p + 4 + 2 * i, clamp16(s.ua[i] * 1000.0f));       // g -> mg
    for (int i = 3; i < 6; i++) put16(p + 4 + 2 * i, clamp16(s.ua[i] * 10.0f));         // dps -> 0.1 dps
    for (int i = 0; i < 3; i++) put16(p + 16 + 2 * i, clamp16(s.fa[i] * 1000.0f));
    for (int i = 3; i < 6; i++) put16(p + 16 + 2 * i, clamp16(s.fa[i] * 10.0f));
    put32(p + 28, (uint32_t)(int32_t)lroundf(s.forceN * 100.0f));                        // N -> 0.01 N
    p[32] = s.status;
  }

  void flush() {
    if (count_ == 0) return;
    packet_[0] = PROTOCOL_VERSION;
    packet_[1] = count_;
    packet_[2] = seq_ & 0xFF;
    packet_[3] = (seq_ >> 8) & 0xFF;
    put32(&packet_[4], deviceId_);
    dataChar_->setValue(packet_, PACKET_HEADER_SIZE + count_ * PACKET_SAMPLE_SIZE);
    dataChar_->notify();
    seq_++;
    sentPackets_++;
    count_ = 0;
  }

  BLEServer* server_ = nullptr;
  BLECharacteristic* dataChar_ = nullptr;
  CommandHandler handler_ = nullptr;
  uint8_t packet_[PACKET_HEADER_SIZE + MAX_SAMPLES_PER_PACKET * PACKET_SAMPLE_SIZE];
  uint8_t count_ = 0;
  uint16_t seq_ = 0;
  uint16_t connId_ = 0;
  uint32_t deviceId_ = 0;
  uint32_t sentPackets_ = 0;
  volatile bool connected_ = false;
  volatile bool streaming_ = false;
  volatile bool restartAdvertising_ = false;
};
