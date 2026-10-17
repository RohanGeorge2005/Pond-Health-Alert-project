# ESP32 IoT Node Hardware Wiring & Calibration Guide

This guide describes how to connect, wire, and calibrate physical water-quality sensors to an **ESP32-WROOM-32D** microcontroller node for automated 24/7 pond monitoring.

---

## 1. Bill of Materials (BOM)

| Component | Model / Specs | Purpose | Interface / Pin |
|---|---|---|---|
| **MCU** | ESP32-WROOM-32D (30-pin DevKit V1) | Data collection, buffer, WiFi/HTTP | Micro-USB / 3.3V Logic |
| **Temperature Sensor** | DS18B20 (Waterproof probe, stainless steel) | Water temperature | OneWire digital (GPIO 4) + 4.7kΩ pull-up |
| **pH Sensor** | DFRobot Gravity Analog pH Sensor V2 / PH-4502C | Water acidity/alkalinity | Analog ADC (GPIO 34) |
| **Dissolved Oxygen Sensor** | DFRobot Gravity Analog Galvanic DO Sensor | Dissolved Oxygen (mg/L) | Analog ADC (GPIO 35) |
| **Ammonia Gas / Headspace** | MQ-137 / MQ-135 Sensor Module | Unionized NH3 concentration | Analog ADC (GPIO 32) |
| **Water Level Sensor** | JSN-SR04T Waterproof Ultrasonic Sensor | Pond depth | Trigger (GPIO 18), Echo (GPIO 19) |
| **Power Supply** | 3.7V 18650 Li-ion battery + Solar TP4056 charger | Continuous rural pond power | 5V VIN / Battery ADC (GPIO 33) |

---

## 2. Wiring Diagram

```
           +---------------------------------------------+
           |               ESP32-WROOM-32D               |
           |                                             |
           |  3V3 ------------------+ VCC (DS18B20)      |
           |                        | VCC (DFRobot pH)   |
           |                        + VCC (DFRobot DO)   |
           |                                             |
           |  GND ------------------+ GND (Common)       |
           |                                             |
           |  GPIO 4  <------------- DATA (DS18B20)      |
           |              [4.7kΩ Resistor between 3V3 & GPIO 4]
           |                                             |
           |  GPIO 34 <------------- Signal AOUT (pH)    |
           |  GPIO 35 <------------- Signal AOUT (DO)    |
           |  GPIO 32 <------------- Signal AOUT (NH3)   |
           |  GPIO 33 <------------- Voltage Divider (Bat)|
           +---------------------------------------------+
```

> [!IMPORTANT]
> **ADC Pin Selection Note:** Always use **ADC1 pins** (GPIO 32, 33, 34, 35, 36, 39) on the ESP32. Do NOT use ADC2 pins (GPIO 0, 2, 4, 12, 13, 14, 15, 25, 26, 27) because ADC2 is disabled when the WiFi radio is active.

---

## 3. Sensor Calibration Procedures

### A. DS18B20 Water Temperature
- **Calibration:** Digital factory calibrated.
- **Verification:** Place in ice water ($0.0^\circ\text{C} \pm 0.5^\circ\text{C}$) and boiling water ($100^\circ\text{C}$ at sea level).
- **Code:** Read using `DallasTemperature` library.

### B. Analog pH Probe (2-Point Calibration)
1. Immerse clean glass probe in standard buffer solution **pH 7.00** at $25^\circ\text{C}$.
2. Measure analog voltage $V_{\text{neutral}}$ (typically $\approx 1.65\text{ V}$).
3. Immerse probe in buffer solution **pH 4.01**.
4. Measure analog voltage $V_{\text{acid}}$ (typically $\approx 2.05\text{ V}$).
5. Compute calibration slope:
   $$\text{Slope} = \frac{7.00 - 4.01}{V_{\text{neutral}} - V_{\text{acid}}}$$
   $$\text{pH} = 7.00 + (V_{\text{neutral}} - V_{\text{measured}}) \times \text{Slope}$$

### C. Galvanic Dissolved Oxygen (DO) Probe
1. Fill membrane cap with $0.5\text{ mol/L NaOH}$ electrolyte solution.
2. Allow probe to polarize in fresh atmospheric air for 5 minutes (100% saturation in air $\approx 8.2\text{ mg/L}$ at $25^\circ\text{C}$).
3. Record $V_{\text{air}}$ (typically $\approx 1.60\text{ V}$).
4. Zero-point check: Place probe in fresh $5\%\text{ sodium sulfite (Na}_2\text{SO}_3)$ deoxygenated solution ($0.0\text{ mg/L}$).
5. Voltage is directly proportional to DO:
   $$\text{DO (mg/L)} = V_{\text{measured}} \times \left(\frac{8.2}{V_{\text{air}}}\right)$$

---

## 4. Flashing Firmware to ESP32

1. Open Arduino IDE or PlatformIO.
2. Install required board and libraries:
   - Board: `esp32` by Espressif Systems
   - Libraries: `ArduinoJson`, `OneWire`, `DallasTemperature`
3. Open `firmware/esp32_pond_monitor.ino`.
4. Update `WIFI_SSID`, `WIFI_PASS`, `SERVER_URL`, and `DEVICE_TOKEN`.
5. Select port and upload at 115200 baud.
