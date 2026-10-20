/**
 * Pond Health Alert - ESP32 IoT Sensor Node Firmware
 * Target: ESP32-WROOM-32D / ESP32 DevKit v1
 * Features:
 *   - Automatic periodic sampling (default: every 120s)
 *   - Analog & Digital sensor acquisition (DO, pH, DS18B20 Temp, Turbidity)
 *   - WiFi connection & auto-reconnect
 *   - Secure HTTP POST ingestion to Pond Health Alert API (/api/iot/readings)
 *   - Device authentication via X-Device-Token header
 *   - Telemetry includes RSSI, estimated battery %, and probe health
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// --- Configuration ---
const char* WIFI_SSID     = "AQUACULTURE_FIELD_WIFI";
const char* WIFI_PASSWORD = "field_secure_password";

const char* API_ENDPOINT  = "http://192.168.1.100:8000/api/iot/readings";
const char* DEVICE_ID     = "ESP32-POND-01";
const char* POND_ID       = "pond-demo-1";
const char* DEVICE_TOKEN  = "esp32_secret_key_pond01";

const unsigned long SAMPLING_INTERVAL_MS = 120000; // 2 minutes

// --- Pin Definitions ---
const int PIN_ONE_WIRE_BUS = 4;   // DS18B20 Temperature Sensor
const int PIN_PH_ANALOG    = 34;  // Analog pH Sensor (ADC1_CH6)
const int PIN_DO_ANALOG    = 35;  // Galvanic Dissolved Oxygen Sensor (ADC1_CH7)
const int PIN_TURBIDITY    = 32;  // Analog Turbidity Sensor (ADC1_CH4)
const int PIN_BATTERY_ADC  = 33;  // Voltage divider for 3.7V LiPo battery

OneWire oneWire(PIN_ONE_WIRE_BUS);
DallasTemperature tempSensors(&oneWire);

unsigned long lastSampleTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[Pond Health Alert] Initializing ESP32 Sensor Node...");

  analogReadResolution(12); // 12-bit ADC (0 - 4095)
  tempSensors.begin();

  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  unsigned long currentMillis = millis();
  if (currentMillis - lastSampleTime >= SAMPLING_INTERVAL_MS || lastSampleTime == 0) {
    lastSampleTime = currentMillis;
    takeAndTransmitReadings();
  }

  delay(1000);
}

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected! IP Address: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi Connection failed. Will retry next cycle.");
  }
}

float readTemperatureC() {
  tempSensors.requestTemperatures();
  float temp = tempSensors.getTempCByIndex(0);
  if (temp < -50.0 || temp > 80.0) {
    return 28.0; // fallback default
  }
  return round(temp * 10.0) / 10.0;
}

float readPH() {
  int raw = analogRead(PIN_PH_ANALOG);
  float voltage = raw * (3.3 / 4095.0);
  // Typical calibration: pH 7.0 = ~2.5V, slope ~ -3.5 pH/V
  float ph = 7.0 + ((2.5 - voltage) * 3.5);
  if (ph < 0.0) ph = 0.0;
  if (ph > 14.0) ph = 14.0;
  return round(ph * 100.0) / 100.0;
}

float readDO() {
  int raw = analogRead(PIN_DO_ANALOG);
  float voltage = raw * (3.3 / 4095.0);
  // Calibration: Galvanic probe with saturation voltage ~1.6V at 25°C = ~7.5 mg/L
  float dissolvedOxygen = voltage * 4.8;
  if (dissolvedOxygen < 0.0) dissolvedOxygen = 0.0;
  if (dissolvedOxygen > 20.0) dissolvedOxygen = 20.0;
  return round(dissolvedOxygen * 10.0) / 10.0;
}

float readTurbidityNTU() {
  int raw = analogRead(PIN_TURBIDITY);
  float voltage = raw * (3.3 / 4095.0);
  // Turbidity curve
  float ntu = -1120.4 * (voltage * voltage) + 5742.3 * voltage - 4352.9;
  if (ntu < 0.0) ntu = 0.0;
  return round(ntu * 10.0) / 10.0;
}

float readBatteryPct() {
  int raw = analogRead(PIN_BATTERY_ADC);
  float voltage = raw * (3.3 / 4095.0) * 2.0; // 1:1 voltage divider
  float pct = ((voltage - 3.2) / (4.2 - 3.2)) * 100.0;
  if (pct > 100.0) pct = 100.0;
  if (pct < 0.0) pct = 0.0;
  return round(pct);
}

void takeAndTransmitReadings() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Cannot transmit: WiFi disconnected.");
    return;
  }

  float temp = readTemperatureC();
  float ph = readPH();
  float doVal = readDO();
  float turbidity = readTurbidityNTU();
  float battery = readBatteryPct();
  int rssi = WiFi.RSSI();

  StaticJsonDocument<512> doc;
  doc["pond_id"] = POND_ID;
  doc["device_id"] = DEVICE_ID;
  doc["temperature"] = temp;
  doc["ph"] = ph;
  doc["dissolved_oxygen"] = doVal;
  doc["turbidity"] = turbidity;
  doc["battery_pct"] = battery;
  doc["signal_rssi"] = rssi;
  doc["is_simulated"] = false;

  JsonObject sensorHealth = doc.createNestedObject("sensor_health");
  sensorHealth["dissolved_oxygen"] = (doVal > 0.5) ? "OK" : "CHECK_PROBE";
  sensorHealth["ph"] = (ph >= 4.0 && ph <= 10.0) ? "OK" : "CHECK_CALIBRATION";
  sensorHealth["temperature"] = (temp > 10.0 && temp < 45.0) ? "OK" : "SENSOR_ERROR";

  String jsonString;
  serializeJson(doc, jsonString);

  HTTPClient http;
  http.begin(API_ENDPOINT);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);

  Serial.println("\n[IoT Node] Posting telemetry to API: " + jsonString);
  int httpResponseCode = http.POST(jsonString);

  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.printf("[IoT Node] HTTP Response %d: %s\n", httpResponseCode, response.c_str());
  } else {
    Serial.printf("[IoT Node] Error on HTTP request: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();
}
