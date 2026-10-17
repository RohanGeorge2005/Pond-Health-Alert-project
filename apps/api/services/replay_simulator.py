import csv
import io
import math
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Generator, Optional
from apps.api.domain.models import SensorReading


class ReplaySimulator:
    """Streams real or synthetic water quality telemetry into the API with controllable fault injection.
    Fault injection modes:
    - DROPOUT: sensor ceases transmitting (tests missing critical readings & CANT_TELL)
    - SPIKE: transient unrealistic electrical spikes (tests physical limits & IQR filtering)
    - STUCK: sensor value remains rigidly constant over hours
    - DRIFT: sensor slowly drifts down or up (tests 7-day linear slope trend warning)
    - STALE: time stops updating (tests >48h staleness detection)
    - OXYGEN_CRASH: rapid DO crash with simulated mortality
    """

    def __init__(self, pond_id: str = "pond-demo-1"):
        self.pond_id = pond_id

    def generate_normal_stream(
        self, days: int = 7, interval_hours: float = 4.0, start_time: Optional[datetime] = None
    ) -> List[SensorReading]:
        """Generates realistic diurnal telemetry (high DO in afternoon, low in dawn)."""
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

        readings = []
        steps = int((days * 24) / interval_hours)

        for step in range(steps):
            t = start_time + timedelta(hours=step * interval_hours)
            hour = t.hour

            # Diurnal solar cycle: DO peaks ~ 4 PM (16:00), lowest ~ 6 AM
            do_baseline = 6.2 + 1.2 * math.sin((hour - 10) * math.pi / 12) + random.gauss(0, 0.1)
            temp = 27.5 + 1.8 * math.sin((hour - 9) * math.pi / 12) + random.gauss(0, 0.1)
            ph = 7.6 + 0.3 * math.sin((hour - 10) * math.pi / 12) + random.gauss(0, 0.05)

            readings.append(
                SensorReading(
                    reading_id=f"sim-{step}",
                    pond_id=self.pond_id,
                    timestamp=t,
                    temperature=round(temp, 2),
                    ph=round(ph, 2),
                    dissolved_oxygen=round(max(0.5, do_baseline), 2),
                    turbidity=round(18.0 + random.gauss(0, 1.5), 1),
                    conductivity=round(380.0 + random.gauss(0, 10.0), 1),
                    ammonia=round(0.015 + abs(random.gauss(0, 0.005)), 3),
                    is_simulated=True,
                )
            )

        return readings

    def inject_fault(
        self, readings: List[SensorReading], fault_type: str
    ) -> List[SensorReading]:
        """Applies designated stress condition to the stream."""
        modified = [r.model_copy() for r in readings]

        if fault_type == "DROPOUT":
            # Strip DO from the last 3 readings to test missing critical handling
            for r in modified[-3:]:
                r.dissolved_oxygen = None

        elif fault_type == "STALE":
            # Shift the timestamp of all readings back by 55 hours
            for r in modified:
                r.timestamp = r.timestamp - timedelta(hours=55)

        elif fault_type == "PHYSICAL_SPIKE":
            # Inject physically impossible pH (16.8) and negative DO (-2.0)
            if modified:
                modified[-1].ph = 16.8
                modified[-1].dissolved_oxygen = -2.0

        elif fault_type == "OXYGEN_CRASH":
            # Steadily crash DO down to 1.8 mg/L over last 5 readings
            crash_values = [4.5, 3.8, 3.1, 2.4, 1.8]
            for i, val in enumerate(crash_values):
                idx = len(modified) - len(crash_values) + i
                if 0 <= idx < len(modified):
                    modified[idx].dissolved_oxygen = val

        elif fault_type == "FALLING_TREND":
            # DO slowly dropping from 6.5 to 5.1 (slope ~ -0.28 mg/L/day)
            n = min(10, len(modified))
            for i in range(n):
                idx = len(modified) - n + i
                modified[idx].dissolved_oxygen = round(6.5 - (i * 0.15), 2)

        return modified
