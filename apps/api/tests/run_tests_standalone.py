import sys
import unittest
from datetime import datetime, timezone, timedelta

# Import models & rules directly
from apps.api.domain.models import (
    SensorReading,
    DailyCheck,
    PhotoInferenceResult,
    HealthStatus,
    ReasonCode,
    FeedingBehavior,
    FishBehavior,
)
from apps.api.domain.config_loader import load_bands_config
from apps.api.domain.decision_engine import evaluate_pond_health
from apps.api.domain.water_rules import (
    validate_reading_physics,
    check_stale_data,
    compute_linear_trend_slope,
)


class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.bands_config = load_bands_config("config/bands.yaml")
        self.now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)

    def test_missing_reading_gives_cant_tell(self):
        result = evaluate_pond_health(
            pond_id="pond-001",
            latest_reading=None,
            historical_readings=[],
            daily_check=None,
            photo_result=None,
            bands_config=self.bands_config,
            now=self.now,
        )
        self.assertEqual(result.status, HealthStatus.CANT_TELL)
        self.assertIn(ReasonCode.MISSING_CRITICAL_READINGS, result.reason_codes)

    def test_stale_reading_gives_cant_tell(self):
        stale_time = self.now - timedelta(hours=49)
        reading = SensorReading(
            pond_id="pond-001",
            timestamp=stale_time,
            temperature=27.0,
            ph=7.5,
            dissolved_oxygen=6.0,
        )
        result = evaluate_pond_health(
            pond_id="pond-001",
            latest_reading=reading,
            historical_readings=[],
            daily_check=None,
            photo_result=None,
            bands_config=self.bands_config,
            now=self.now,
        )
        self.assertEqual(result.status, HealthStatus.CANT_TELL)
        self.assertIn(ReasonCode.STALE_DATA, result.reason_codes)

    def test_impossible_values_give_cant_tell(self):
        reading = SensorReading(
            pond_id="pond-001",
            timestamp=self.now,
            temperature=28.0,
            ph=-1.0,  # Physically impossible pH
            dissolved_oxygen=6.0,
        )
        result = evaluate_pond_health(
            pond_id="pond-001",
            latest_reading=reading,
            historical_readings=[],
            daily_check=None,
            photo_result=None,
            bands_config=self.bands_config,
            now=self.now,
        )
        self.assertEqual(result.status, HealthStatus.CANT_TELL)
        self.assertIn(ReasonCode.PHYSICALLY_IMPOSSIBLE_VALUE, result.reason_codes)

    def test_optimal_readings_give_green(self):
        reading = SensorReading(
            pond_id="pond-001",
            timestamp=self.now,
            temperature=27.5,
            ph=7.5,
            dissolved_oxygen=6.5,
            turbidity=15.0,
            conductivity=350.0,
            ammonia=0.02,
        )
        daily = DailyCheck(
            pond_id="pond-001",
            timestamp=self.now,
            feeding=FeedingBehavior.NORMAL,
            behavior=FishBehavior.NORMAL,
            dead_fish_count=0,
        )
        result = evaluate_pond_health(
            pond_id="pond-001",
            latest_reading=reading,
            historical_readings=[],
            daily_check=daily,
            photo_result=None,
            bands_config=self.bands_config,
            now=self.now,
        )
        self.assertEqual(result.status, HealthStatus.GREEN)
        self.assertIn(ReasonCode.OPTIMAL_WATER_QUALITY, result.reason_codes)

    def test_critical_low_do_gives_red(self):
        reading = SensorReading(
            pond_id="pond-001",
            timestamp=self.now,
            temperature=27.5,
            ph=7.5,
            dissolved_oxygen=2.1,  # Critical Red < 3.0
        )
        result = evaluate_pond_health(
            pond_id="pond-001",
            latest_reading=reading,
            historical_readings=[],
            daily_check=None,
            photo_result=None,
            bands_config=self.bands_config,
            now=self.now,
        )
        self.assertEqual(result.status, HealthStatus.RED)
        self.assertIn(ReasonCode.CRITICAL_LOW_DO, result.reason_codes)

    def test_two_amber_parameters_give_red(self):
        # Amber temp (23.5 C) + Amber DO (4.0 mg/L) -> RED
        reading = SensorReading(
            pond_id="pond-001",
            timestamp=self.now,
            temperature=23.5,
            ph=7.5,
            dissolved_oxygen=4.0,
        )
        result = evaluate_pond_health(
            pond_id="pond-001",
            latest_reading=reading,
            historical_readings=[],
            daily_check=None,
            photo_result=None,
            bands_config=self.bands_config,
            now=self.now,
        )
        self.assertEqual(result.status, HealthStatus.RED)
        self.assertIn(ReasonCode.MULTIPLE_AMBER_PARAMETERS, result.reason_codes)

    def test_amber_plus_dead_fish_gives_red(self):
        reading = SensorReading(
            pond_id="pond-001",
            timestamp=self.now,
            temperature=23.5,  # Amber
            ph=7.5,
            dissolved_oxygen=6.0,
        )
        daily = DailyCheck(
            pond_id="pond-001",
            timestamp=self.now,
            feeding=FeedingBehavior.NORMAL,
            behavior=FishBehavior.NORMAL,
            dead_fish_count=2,  # Dead fish count > 0 with amber -> RED
        )
        result = evaluate_pond_health(
            pond_id="pond-001",
            latest_reading=reading,
            historical_readings=[],
            daily_check=daily,
            photo_result=None,
            bands_config=self.bands_config,
            now=self.now,
        )
        self.assertEqual(result.status, HealthStatus.RED)
        self.assertIn(ReasonCode.AMBER_WITH_RISING_MORTALITY, result.reason_codes)

    def test_photo_failed_gate_cannot_be_green(self):
        reading = SensorReading(
            pond_id="pond-001",
            timestamp=self.now,
            temperature=28.0,
            ph=7.5,
            dissolved_oxygen=6.5,
        )
        failed_photo = PhotoInferenceResult(
            pond_id="pond-001",
            timestamp=self.now,
            passed_gate=False,
            gate_failure_reasons=["BLUR_DETECTED"],
        )
        result = evaluate_pond_health(
            pond_id="pond-001",
            latest_reading=reading,
            historical_readings=[],
            daily_check=None,
            photo_result=failed_photo,
            bands_config=self.bands_config,
            now=self.now,
        )
        self.assertNotEqual(result.status, HealthStatus.GREEN)
        self.assertEqual(result.status, HealthStatus.AMBER)
        self.assertIn(ReasonCode.PHOTO_FAILED_QUALITY_GATE, result.reason_codes)


if __name__ == "__main__":
    unittest.main()
