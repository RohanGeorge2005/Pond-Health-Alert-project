# Pond Health Alert - ESP32 Hardware & Firmware Guide

This directory contains the firmware and wiring specifications for the automatic IoT pond monitoring node.

## Hardware Components
1. **Microcontroller:** ESP32-WROOM-32D / ESP32 DevKit v1 (with integrated 2.4GHz Wi-Fi).
2. **Dissolved Oxygen Sensor:** Galvanic DO probe (DFRobot / Atlas Scientific analog kit).
3. **pH Sensor:** Industrial gel-filled BNC pH probe with signal conditioning board.
4. **Water Temperature Sensor:** Waterproof DS18B20 digital temperature probe (Dallas 1-Wire).
5. **Turbidity Sensor:** Optical turbidity sensor (0–4000 NTU analog).
6. **Power Source:** 3.7V 18650 Li-ion battery or 6V 5W solar panel with TP4056 charge controller.
7. **Enclosure:** IP67 waterproof junction box with waterproof cable glands.

---

## Pin Connection Mapping
| Sensor / Peripheral | ESP32 GPIO Pin | Description |
|:-------------------|:---------------|:------------|
| DS18B20 Temp Data  | GPIO 4         | 1-Wire data bus (with 4.7kΩ pull-up to 3.3V) |
| pH Probe Analog    | GPIO 34 (ADC1) | Analog voltage signal (0 - 3.3V) |
| DO Probe Analog    | GPIO 35 (ADC1) | Analog voltage signal (0 - 3.3V) |
| Turbidity Analog   | GPIO 32 (ADC1) | Analog voltage signal (0 - 3.3V) |
| Battery Voltage    | GPIO 33 (ADC1) | 1:1 voltage divider (two 100kΩ resistors) |
| Power Supply (VCC) | 3.3V / VIN     | Regulated 3.3V or 5V power bus |
| Ground (GND)       | GND            | Common ground |

---

## Telemetry Ingestion API Spec
- **Endpoint:** `POST /api/iot/readings`
- **Headers:**
  - `Content-Type: application/json`
  - `X-Device-Token: esp32_secret_key_pond01` (or device-specific key registered in backend)
- **JSON Payload:**
```json
{
  "pond_id": "pond-demo-1",
  "device_id": "ESP32-POND-01",
  "temperature": 27.8,
  "ph": 7.42,
  "dissolved_oxygen": 5.8,
  "turbidity": 14.5,
  "battery_pct": 92.0,
  "signal_rssi": -64,
  "is_simulated": false,
  "sensor_health": {
    "dissolved_oxygen": "OK",
    "ph": "OK",
    "temperature": "OK"
  }
}
```

---

## Flashing Instructions
1. Install Arduino IDE with **ESP32 Board Support** (`https://dl.espressif.com/dl/package_esp32_index.json`).
2. Install required Arduino libraries:
   - `ArduinoJson` (v6.x or v7.x)
   - `OneWire`
   - `DallasTemperature`
3. Open `esp32_firmware.ino` in Arduino IDE.
4. Update `WIFI_SSID`, `WIFI_PASSWORD`, and `API_ENDPOINT` to match your local network and server address.
5. Select Board: **ESP32 Dev Module**, choose the USB COM Port, and click **Upload**.
