import pytest
from datetime import datetime, timezone, timedelta
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


@pytest.fixture
def bands_config():
    return load_bands_config("config/bands.yaml")


@pytest.fixture
def base_time():
    return datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)


def test_missing_reading_gives_cant_tell(bands_config, base_time):
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=None,
        historical_readings=[],
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    assert result.status == HealthStatus.CANT_TELL
    assert ReasonCode.MISSING_CRITICAL_READINGS in result.reason_codes


def test_stale_reading_older_than_48h_gives_cant_tell(bands_config, base_time):
    old_time = base_time - timedelta(hours=49)
    stale_reading = SensorReading(
        pond_id="pond-101",
        timestamp=old_time,
        temperature=27.0,
        ph=7.5,
        dissolved_oxygen=6.0,
    )
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=stale_reading,
        historical_readings=[],
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    assert result.status == HealthStatus.CANT_TELL
    assert ReasonCode.STALE_DATA in result.reason_codes


def test_impossible_values_give_cant_tell(bands_config, base_time):
    impossible_reading = SensorReading(
        pond_id="pond-101",
        timestamp=base_time,
        temperature=28.0,
        ph=16.5,  # pH cannot exceed 14
        dissolved_oxygen=6.0,
    )
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=impossible_reading,
        historical_readings=[],
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    assert result.status == HealthStatus.CANT_TELL
    assert ReasonCode.PHYSICALLY_IMPOSSIBLE_VALUE in result.reason_codes


def test_optimal_readings_give_green(bands_config, base_time):
    optimal_reading = SensorReading(
        pond_id="pond-101",
        timestamp=base_time,
        temperature=27.5,
        ph=7.4,
        dissolved_oxygen=6.5,
        turbidity=15.0,
        conductivity=350.0,
        ammonia=0.02,
    )
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=optimal_reading,
        historical_readings=[],
        daily_check=DailyCheck(
            pond_id="pond-101",
            timestamp=base_time,
            feeding=FeedingBehavior.NORMAL,
            behavior=FishBehavior.NORMAL,
            dead_fish_count=0,
        ),
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    assert result.status == HealthStatus.GREEN
    assert ReasonCode.OPTIMAL_WATER_QUALITY in result.reason_codes


def test_single_amber_yields_amber(bands_config, base_time):
    # Temp in 23.5 C is amber
    reading = SensorReading(
        pond_id="pond-101",
        timestamp=base_time,
        temperature=23.5,
        ph=7.2,
        dissolved_oxygen=6.0,
    )
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=reading,
        historical_readings=[],
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    assert result.status == HealthStatus.AMBER
    assert ReasonCode.SUBOPTIMAL_TEMP in result.reason_codes


def test_critical_low_do_yields_red(bands_config, base_time):
    reading = SensorReading(
        pond_id="pond-101",
        timestamp=base_time,
        temperature=27.0,
        ph=7.2,
        dissolved_oxygen=2.4,  # Red band < 3.0
    )
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=reading,
        historical_readings=[],
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    assert result.status == HealthStatus.RED
    assert ReasonCode.CRITICAL_LOW_DO in result.reason_codes


def test_two_ambers_yield_red(bands_config, base_time):
    # Temp amber (23.5) + DO amber (4.2 mg/L)
    reading = SensorReading(
        pond_id="pond-101",
        timestamp=base_time,
        temperature=23.5,
        ph=7.2,
        dissolved_oxygen=4.2,
    )
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=reading,
        historical_readings=[],
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    assert result.status == HealthStatus.RED
    assert ReasonCode.MULTIPLE_AMBER_PARAMETERS in result.reason_codes


def test_amber_plus_dead_fish_yields_red(bands_config, base_time):
    reading = SensorReading(
        pond_id="pond-101",
        timestamp=base_time,
        temperature=23.5,  # Amber
        ph=7.2,
        dissolved_oxygen=6.0,
    )
    daily = DailyCheck(
        pond_id="pond-101",
        timestamp=base_time,
        feeding=FeedingBehavior.NORMAL,
        behavior=FishBehavior.NORMAL,
        dead_fish_count=2,  # Dead fish count > 0 with amber -> RED
    )
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=reading,
        historical_readings=[],
        daily_check=daily,
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    assert result.status == HealthStatus.RED
    assert ReasonCode.AMBER_WITH_RISING_MORTALITY in result.reason_codes


def test_photo_failed_gate_cannot_be_green(bands_config, base_time):
    reading = SensorReading(
        pond_id="pond-101",
        timestamp=base_time,
        temperature=28.0,
        ph=7.5,
        dissolved_oxygen=6.5,
    )
    failed_photo = PhotoInferenceResult(
        pond_id="pond-101",
        timestamp=base_time,
        passed_gate=False,
        gate_failure_reasons=["BLUR_DETECTED_VARIANCE_LOW"],
    )
    result = evaluate_pond_health(
        pond_id="pond-101",
        latest_reading=reading,
        historical_readings=[],
        daily_check=None,
        photo_result=failed_photo,
        bands_config=bands_config,
        now=base_time,
    )
    # Never green when photo quality gate fails
    assert result.status != HealthStatus.GREEN
    assert result.status == HealthStatus.AMBER
    assert ReasonCode.PHOTO_FAILED_QUALITY_GATE in result.reason_codes


def test_falling_do_trend_warning_triggers_early(bands_config, base_time):
    # Historical readings falling from 6.8 to 5.2 over 5 days (slope ~ -0.32 mg/L/day)
    history = [
        SensorReading(pond_id="pond-1", timestamp=base_time - timedelta(days=5), dissolved_oxygen=6.8, temperature=28.0, ph=7.2),
        SensorReading(pond_id="pond-1", timestamp=base_time - timedelta(days=4), dissolved_oxygen=6.4, temperature=28.0, ph=7.2),
        SensorReading(pond_id="pond-1", timestamp=base_time - timedelta(days=3), dissolved_oxygen=6.0, temperature=28.0, ph=7.2),
        SensorReading(pond_id="pond-1", timestamp=base_time - timedelta(days=2), dissolved_oxygen=5.6, temperature=28.0, ph=7.2),
    ]
    latest = SensorReading(
        pond_id="pond-1",
        timestamp=base_time,
        dissolved_oxygen=5.2,  # Current reading is still green (>5.0)!
        temperature=28.0,
        ph=7.2,
    )
    result = evaluate_pond_health(
        pond_id="pond-1",
        latest_reading=latest,
        historical_readings=history,
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=base_time,
    )
    # The trend rule warns before the fixed limit is crossed
    assert ReasonCode.FALLING_DO_TREND in result.reason_codes
    assert len(result.trend_warnings) > 0
    assert result.status == HealthStatus.AMBER
