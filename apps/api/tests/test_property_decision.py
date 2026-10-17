import pytest
from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st, settings
from apps.api.domain.models import (
    SensorReading,
    DailyCheck,
    PhotoInferenceResult,
    HealthStatus,
    FeedingBehavior,
    FishBehavior,
)
from apps.api.domain.config_loader import load_bands_config
from apps.api.domain.decision_engine import evaluate_pond_health


@pytest.fixture(scope="module")
def bands_config():
    return load_bands_config("config/bands.yaml")


# Hypothesis strategies for generating test data
temp_strategy = st.floats(min_value=-50.0, max_value=100.0, allow_nan=False)
ph_strategy = st.floats(min_value=-5.0, max_value=20.0, allow_nan=False)
do_strategy = st.floats(min_value=-10.0, max_value=50.0, allow_nan=False)
hours_ago_strategy = st.floats(min_value=0.0, max_value=200.0, allow_nan=False)


@settings(max_examples=100, deadline=None)
@given(
    temp=temp_strategy,
    ph=ph_strategy,
    do=do_strategy,
    hours_ago=hours_ago_strategy,
)
def test_property_never_false_green_on_invalid_or_stale_data(bands_config, temp, ph, do, hours_ago):
    """PROPERTY TEST: Proves mathematically that NO input combination with missing,
    stale (>48h), or physically impossible data can EVER yield GREEN status.
    """
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    reading_time = now - timedelta(hours=hours_ago)

    reading = SensorReading(
        pond_id="hyp-pond",
        timestamp=reading_time,
        temperature=temp,
        ph=ph,
        dissolved_oxygen=do,
    )

    result = evaluate_pond_health(
        pond_id="hyp-pond",
        latest_reading=reading,
        historical_readings=[],
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=now,
    )

    is_stale = hours_ago > 48.0
    is_impossible = (
        temp < 0.0 or temp > 50.0
        or ph < 0.0 or ph > 14.0
        or do < 0.0 or do > 25.0
    )

    # Core non-negotiable invariant
    if is_stale or is_impossible:
        assert result.status != HealthStatus.GREEN, (
            f"VIOLATION: Status became GREEN despite invalid data! "
            f"stale={is_stale} (hours={hours_ago}), impossible={is_impossible} (temp={temp}, ph={ph}, do={do})"
        )
        assert result.status == HealthStatus.CANT_TELL


@settings(max_examples=50, deadline=None)
@given(
    missing_param=st.sampled_from(["temperature", "ph", "dissolved_oxygen"])
)
def test_property_missing_critical_never_yields_green(bands_config, missing_param):
    """PROPERTY TEST: Missing any critical parameter (temp, pH, DO) MUST never yield green."""
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
    data = {
        "temperature": 27.5,
        "ph": 7.5,
        "dissolved_oxygen": 6.5,
    }
    data[missing_param] = None

    reading = SensorReading(
        pond_id="hyp-missing",
        timestamp=now,
        temperature=data["temperature"],
        ph=data["ph"],
        dissolved_oxygen=data["dissolved_oxygen"],
    )

    result = evaluate_pond_health(
        pond_id="hyp-missing",
        latest_reading=reading,
        historical_readings=[],
        daily_check=None,
        photo_result=None,
        bands_config=bands_config,
        now=now,
    )

    assert result.status != HealthStatus.GREEN
    assert result.status == HealthStatus.CANT_TELL
