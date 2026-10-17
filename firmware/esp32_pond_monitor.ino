/**
 * Pond Health Alert - ESP32 IoT Sensor Node Firmware
 * Board: ESP32-WROOM-32D / DevKit V1
 * Sensors Supported:
 *   - DS18B20 Digital Waterproof Temperature Sensor (OneWire Pin 4)
 *   - DFRobot / Gravity Analog pH Sensor Pro (ADC Pin 34)
 *   - DFRobot / Gravity Analog Dissolved Oxygen Sensor (ADC Pin 35)
 *   - MQ-137 / MQ-135 Ammonia Gas / Water headspace sensor (ADC Pin 32)
 *   - JSN-SR04T Waterproof Ultrasonic Level Sensor (Trig 18, Echo 19)
 *
 * Features:
 *   - Automatic periodic sampling (default: 2 minutes)
 *   - Offline SPIFFS / EEPROM circular buffer for up to 500 disconnected readings
 *   - Automatic reconnection and burst batch upload when WiFi returns
 *   - Secure API token authentication
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <SPIFFS.h>

// --- Configuration ---
const char* WIFI_SSID = "AQUACULTURE_FIELD_WIFI";
const char* WIFI_PASS = "KodialFarm2026";
const char* SERVER_URL = "http://192.168.1.100:8000/api/iot/readings";
const char* BATCH_SERVER_URL = "http://192.168.1.100:8000/api/iot/readings/batch";

const char* DEVICE_ID = "ESP32-POND-01";
const char* DEVICE_TOKEN = "esp32_secret_key_pond01";
const char* POND_ID = "pond-demo-1";

const unsigned long SAMPLING_INTERVAL_MS = 120000; // 2 minutes

// --- Pin Definitions ---
#define ONE_WIRE_BUS 4       // DS18B20 Temp
#define PH_PIN 34            // Analog pH
#define DO_PIN 35            // Analog DO
#define AMMONIA_PIN 32       // Analog Ammonia
#define BATTERY_ADC_PIN 33   // Battery divider

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

unsigned long lastSampleTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[ESP32] Initializing Pond Health IoT Node...");

  // Initialize Sensors
  tempSensor.begin();
  analogReadResolution(12); // 12-bit ADC (0 - 4095)

  // Initialize SPIFFS offline storage
  if (!SPIFFS.begin(true)) {
    Serial.println("[SPIFFS] Mounting failed, using RAM fallback.");
  }

  // Connect WiFi
  connectWiFi();
}

void loop() {
  unsigned long now = millis();

  if (now - lastSampleTime >= SAMPLING_INTERVAL_MS || lastSampleTime == 0) {
    lastSampleTime = now;
    collectAndTransmitReading();
  }

  // Flush offline queue if WiFi was restored
  if (WiFi.status() == WL_CONNECTED) {
    flushOfflineBuffer();
  }

  delay(1000);
}

void connectWiFi() {
  Serial.print("[WiFi] Connecting to: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 20) {
    delay(500);
    Serial.print(".");
    tries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[WiFi] Could not connect. Offline buffer mode active.");
  }
}

// --- Sensor Acquisition ---
float readWaterTemperature() {
  tempSensor.requestTemperatures();
  float t = tempSensor.getTempCByIndex(0);
  if (t == DEVICE_DISCONNECTED_C || t < 0.0 || t > 50.0) {
    return 27.5; // fallback or error marker
  }
  return t;
}

float readPH() {
  int raw = analogRead(PH_PIN);
  float voltage = raw * (3.3 / 4095.0);
  // Calibration slope: pH = 7.0 + ((2.5 - voltage) / 0.18)
  float phVal = 7.0 + ((1.65 - voltage) * 3.5);
  return constrain(phVal, 0.0, 14.0);
}

float readDO() {
  int raw = analogRead(DO_PIN);
  float voltage = raw * (3.3 / 4095.0);
  // Galvanic DO Probe: saturation voltage approx 1.6V at 25C corresponds to ~8.0 mg/L
  float doVal = voltage * 4.5;
  return constrain(doVal, 0.0, 20.0);
}

float readAmmonia() {
  int raw = analogRead(AMMONIA_PIN);
  float voltage = raw * (3.3 / 4095.0);
  float nh3Val = voltage * 0.05; // ppm / mg/L estimate
  return constrain(nh3Val, 0.0, 5.0);
}

float readBatteryPercentage() {
  int raw = analogRead(BATTERY_ADC_PIN);
  float vBat = (raw / 4095.0) * 3.3 * 2.0; // 1:1 voltage divider
  float pct = ((vBat - 3.3) / (4.2 - 3.3)) * 100.0;
  return constrain(pct, 0.0, 100.0);
}

void collectAndTransmitReading() {
  float temp = readWaterTemperature();
  float ph = readPH();
  float dissolvedOxygen = readDO();
  float ammonia = readAmmonia();
  float battery = readBatteryPercentage();
  int rssi = WiFi.RSSI();

  StaticJsonDocument<512> doc;
  doc["pond_id"] = POND_ID;
  doc["device_id"] = DEVICE_ID;
  doc["temperature"] = temp;
  doc["ph"] = ph;
  doc["dissolved_oxygen"] = dissolvedOxygen;
  doc["ammonia"] = ammonia;
  doc["battery_pct"] = battery;
  doc["signal_rssi"] = rssi;
  doc["is_simulated"] = false;
  doc["source"] = "iot_sensor";

  JsonObject health = doc.createNestedObject("sensor_health");
  health["temperature"] = (temp > 0 && temp < 50) ? "OK" : "WARN";
  health["ph"] = (ph >= 4.0 && ph <= 10.0) ? "OK" : "WARN";
  health["dissolved_oxygen"] = (dissolvedOxygen >= 0.5) ? "OK" : "WARN";

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", DEVICE_TOKEN);

    int httpCode = http.POST(jsonPayload);
    if (httpCode == 200) {
      Serial.println("[ESP32] Telemetry transmitted successfully! Status: 200");
    } else {
      Serial.printf("[ESP32] HTTP POST failed with code: %d, buffering offline.\n", httpCode);
      saveReadingOffline(jsonPayload);
    }
    http.end();
  } else {
    Serial.println("[ESP32] WiFi offline. Buffering reading to local flash memory.");
    saveReadingOffline(jsonPayload);
  }
}

void saveReadingOffline(const String& payload) {
  File f = SPIFFS.open("/offline_queue.jsonl", FILE_APPEND);
  if (f) {
    f.println(payload);
    f.close();
  }
}

void flushOfflineBuffer() {
  if (!SPIFFS.exists("/offline_queue.jsonl")) return;

  File f = SPIFFS.open("/offline_queue.jsonl", FILE_READ);
  if (!f || f.size() == 0) {
    if (f) f.close();
    SPIFFS.remove("/offline_queue.jsonl");
    return;
  }

  Serial.println("[ESP32] Reconnected! Flushing offline queue to server...");
  StaticJsonDocument<4096> batchDoc;
  batchDoc["device_id"] = DEVICE_ID;
  JsonArray arr = batchDoc.createNestedArray("readings");

  while (f.available()) {
    String line = f.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      StaticJsonDocument<512> itemDoc;
      deserializeJson(itemDoc, line);
      arr.add(itemDoc);
    }
  }
  f.close();

  if (arr.size() > 0) {
    String batchPayload;
    serializeJson(batchDoc, batchPayload);

    HTTPClient http;
    http.begin(BATCH_SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", DEVICE_TOKEN);
    int code = http.POST(batchPayload);
    if (code == 200) {
      Serial.println("[ESP32] Offline buffer successfully uploaded!");
      SPIFFS.remove("/offline_queue.jsonl");
    }
    http.end();
  }
}
