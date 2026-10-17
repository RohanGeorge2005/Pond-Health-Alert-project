import time
import math
import random
import requests
import argparse
from datetime import datetime, timezone
from typing import Optional

API_BASE_URL = "http://localhost:8000"
DEVICE_ID = "ESP32-POND-01"
DEVICE_TOKEN = "esp32_secret_key_pond01"
POND_ID = "pond-demo-1"


def generate_sensor_values(step: int, mode: str = "normal") -> dict:
    """Generates realistic sensor readings based on mode."""
    # Base diurnal oscillation
    hour = (datetime.now().hour + step / 10.0) % 24
    base_temp = 27.5 + 1.8 * math.sin((hour - 9) * math.pi / 12) + random.gauss(0, 0.05)
    base_ph = 7.5 + 0.3 * math.sin((hour - 10) * math.pi / 12) + random.gauss(0, 0.02)
    base_do = 6.2 + 1.2 * math.sin((hour - 10) * math.pi / 12) + random.gauss(0, 0.05)
    base_ammonia = 0.018 + abs(random.gauss(0, 0.002))
    base_turbidity = 16.5 + random.gauss(0, 0.5)

    if mode == "hypoxia_crash":
        # Rapid nocturnal oxygen crash simulating phytoplankton collapse
        base_do = max(1.2, 5.0 - (step * 0.7))
    elif mode == "rising_ammonia":
        # Overfeeding / organic waste decomposition spike
        base_ammonia = min(0.35, 0.02 + (step * 0.04))
    elif mode == "acidic_spike":
        # Heavy rain runoff causing pH drop
        base_ph = max(5.2, 7.2 - (step * 0.3))
    elif mode == "sensor_failure":
        # Impossible values
        base_ph = 16.5
        base_do = -1.0

    return {
        "temperature": round(base_temp, 2),
        "ph": round(base_ph, 2),
        "dissolved_oxygen": round(max(0.0, base_do), 2),
        "ammonia": round(base_ammonia, 3),
        "turbidity": round(base_turbidity, 1),
        "water_level_cm": round(120.0 + random.gauss(0, 0.5), 1),
        "battery_pct": round(max(15.0, 98.0 - (step * 0.1)), 1),
        "signal_rssi": int(-62 + random.randint(-4, 4)),
    }


def transmit_reading(pond_id: str, device_id: str, token: str, values: dict, is_simulated: bool = True):
    payload = {
        "pond_id": pond_id,
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": values["temperature"],
        "ph": values["ph"],
        "dissolved_oxygen": values["dissolved_oxygen"],
        "ammonia": values["ammonia"],
        "turbidity": values["turbidity"],
        "water_level_cm": values["water_level_cm"],
        "battery_pct": values["battery_pct"],
        "signal_rssi": values["signal_rssi"],
        "sensor_health": {
            "dissolved_oxygen": "OK" if values["dissolved_oxygen"] >= 0 else "FAIL",
            "ph": "OK" if 0 <= values["ph"] <= 14 else "FAIL",
            "temperature": "OK",
            "ammonia": "OK",
        },
        "is_simulated": is_simulated,
        "source": "iot_simulator",
    }

    headers = {
        "X-Device-Token": token,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(f"{API_BASE_URL}/api/iot/readings", json=payload, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Transmitted: DO={values['dissolved_oxygen']} mg/L, pH={values['ph']}, Temp={values['temperature']}°C -> Assessment: {data.get('assessment_status')} ({data.get('reason_codes')})")
        else:
            print(f"Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Transmission failed: {e}")


def run_continuous_simulation(interval_seconds: int = 5, total_steps: int = 10, mode: str = "normal"):
    print(f"=== Starting IoT Sensor Simulator ===")
    print(f"Device: {DEVICE_ID} | Pond: {POND_ID} | Mode: {mode} | Interval: {interval_seconds}s")
    for step in range(total_steps):
        vals = generate_sensor_values(step, mode=mode)
        transmit_reading(POND_ID, DEVICE_ID, DEVICE_TOKEN, vals)
        if step < total_steps - 1:
            time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pond Health IoT Sensor Simulator")
    parser.add_argument("--interval", type=int, default=3, help="Interval in seconds between transmissions")
    parser.add_argument("--steps", type=int, default=10, help="Total readings to stream")
    parser.add_argument("--mode", type=str, default="normal", choices=["normal", "hypoxia_crash", "rising_ammonia", "acidic_spike", "sensor_failure"])
    args = parser.parse_args()
    run_continuous_simulation(args.interval, args.steps, args.mode)
