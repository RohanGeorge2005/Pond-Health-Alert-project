import pytest
from datetime import datetime, timezone, timedelta
from apps.api.domain.models import SensorReading, HealthStatus, ReasonCode
from apps.api.domain.config_loader import load_bands_config
from apps.api.domain.water_rules import (
    validate_reading_physics,
    check_stale_data,
    evaluate_parameter_band,
    compute_linear_trend_slope,
)

@pytest.fixture
def bands_cfg():
    return load_bands_config("config/bands.yaml")


def test_physics_validation_detects_all_extremes(bands_cfg):
    now = datetime.now(timezone.utc)
    # Impossible pH and negative DO
    bad_reading = SensorReading(
        pond_id="p-1",
        timestamp=now,
        ph=-1.0,
        dissolved_oxygen=-0.5,
        temperature=55.0,
    )
    is_valid, violations = validate_reading_physics(bad_reading, bands_cfg)
    assert is_valid is False
    assert len(violations) >= 3


def test_stale_data_boundary_conditions():
    now = datetime.now(timezone.utc)
    # Exactly 47 hours old -> not stale
    fresh_time = now - timedelta(hours=47)
    is_stale, hours = check_stale_data(fresh_time, now, stale_hours_threshold=48.0)
    assert is_stale is False
    assert 46.9 <= hours <= 47.1

    # 49 hours old -> stale
    old_time = now - timedelta(hours=49)
    is_stale, hours = check_stale_data(old_time, now, stale_hours_threshold=48.0)
    assert is_stale is True
    assert 48.9 <= hours <= 49.1


def test_parameter_band_evaluations(bands_cfg):
    params_cfg = bands_cfg["parameters"]

    # DO optimal: 6.5 mg/L -> GREEN
    score_do_green = evaluate_parameter_band("dissolved_oxygen", 6.5, params_cfg["dissolved_oxygen"])
    assert score_do_green.band == HealthStatus.GREEN

    # DO warning: 4.0 mg/L -> AMBER (LOW_DO)
    score_do_amber = evaluate_parameter_band("dissolved_oxygen", 4.0, params_cfg["dissolved_oxygen"])
    assert score_do_amber.band == HealthStatus.AMBER
    assert score_do_amber.reason_code == ReasonCode.LOW_DO

    # DO critical: 2.0 mg/L -> RED (CRITICAL_LOW_DO)
    score_do_red = evaluate_parameter_band("dissolved_oxygen", 2.0, params_cfg["dissolved_oxygen"])
    assert score_do_red.band == HealthStatus.RED
    assert score_do_red.reason_code == ReasonCode.CRITICAL_LOW_DO

    # pH optimal: 7.5 -> GREEN
    score_ph_green = evaluate_parameter_band("ph", 7.5, params_cfg["ph"])
    assert score_ph_green.band == HealthStatus.GREEN

    # pH low extreme: 5.5 -> RED
    score_ph_red = evaluate_parameter_band("ph", 5.5, params_cfg["ph"])
    assert score_ph_red.band == HealthStatus.RED


def test_linear_trend_slope_calculation():
    base = datetime.now(timezone.utc)
    # 5 readings dropping DO by 0.4 mg/L every day
    readings = [
        SensorReading(pond_id="p-1", timestamp=base - timedelta(days=4), dissolved_oxygen=6.8, temperature=28.0, ph=7.2),
        SensorReading(pond_id="p-1", timestamp=base - timedelta(days=3), dissolved_oxygen=6.4, temperature=28.0, ph=7.2),
        SensorReading(pond_id="p-1", timestamp=base - timedelta(days=2), dissolved_oxygen=6.0, temperature=28.0, ph=7.2),
        SensorReading(pond_id="p-1", timestamp=base - timedelta(days=1), dissolved_oxygen=5.6, temperature=28.0, ph=7.2),
        SensorReading(pond_id="p-1", timestamp=base, dissolved_oxygen=5.2, temperature=28.0, ph=7.2),
    ]
    trend = compute_linear_trend_slope(readings, "dissolved_oxygen", window_days=7)
    assert trend is not None
    assert trend.slope_per_day < -0.3
    assert trend.warning_code == ReasonCode.FALLING_DO_TREND
    assert trend.projected_days_to_breach is not None
    assert trend.projected_days_to_breach > 0
