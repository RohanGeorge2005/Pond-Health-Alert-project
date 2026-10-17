from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from datetime import datetime, timezone
from apps.api.domain.models import (
    SensorReading,
    HealthStatus,
    ReasonCode,
    ParameterScore,
    TrendFlag,
    DataQualitySummary,
)


def validate_reading_physics(
    reading: SensorReading, bands_config: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Checks for physically impossible values against configured limits.
    Returns (is_physically_possible, list_of_violations).
    """
    violations = []
    params_cfg = bands_config.get("parameters", {})

    for param, cfg in params_cfg.items():
        val = getattr(reading, param, None)
        if val is None:
            continue
        limits = cfg.get("physical_limits", {})
        min_val = limits.get("min")
        max_val = limits.get("max")
        if min_val is not None and val < min_val:
            violations.append(f"{param}={val} below physical min {min_val}")
        if max_val is not None and val > max_val:
            violations.append(f"{param}={val} above physical max {max_val}")

    return len(violations) == 0, violations


def check_stale_data(
    reading_timestamp: datetime,
    current_time: Optional[datetime] = None,
    stale_hours_threshold: float = 48.0,
) -> Tuple[bool, float]:
    """Returns (is_stale, elapsed_hours)."""
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Ensure timezone awareness compatibility
    if reading_timestamp.tzinfo is None and current_time.tzinfo is not None:
        reading_timestamp = reading_timestamp.replace(tzinfo=timezone.utc)
    elif reading_timestamp.tzinfo is not None and current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    elapsed_seconds = (current_time - reading_timestamp).total_seconds()
    elapsed_hours = max(0.0, elapsed_seconds / 3600.0)
    return elapsed_hours > stale_hours_threshold, elapsed_hours


def evaluate_parameter_band(
    param_name: str,
    value: Optional[float],
    param_config: Dict[str, Any],
) -> ParameterScore:
    """Evaluates a single parameter value against guidance bands (green, amber, red)."""
    if value is None:
        return ParameterScore(
            parameter=param_name,
            value=None,
            band=HealthStatus.CANT_TELL,
            reason_code=ReasonCode.MISSING_CRITICAL_READINGS,
            detail=f"{param_name} reading is missing",
        )

    bands = param_config.get("bands", {})
    green = bands.get("green", {})
    amber = bands.get("amber", {})

    # 1. Check Green
    if "min" in green and "max" in green:
        if green["min"] <= value <= green["max"]:
            return ParameterScore(
                parameter=param_name,
                value=value,
                band=HealthStatus.GREEN,
                reason_code=ReasonCode.OPTIMAL_WATER_QUALITY,
                detail=f"{param_name} is in optimal range ({green['min']}-{green['max']})",
            )

    # 2. Check Amber
    if "min" in amber and "max" in amber:
        if amber["min"] <= value <= amber["max"]:
            code = (
                ReasonCode.LOW_DO
                if param_name == "dissolved_oxygen"
                else (
                    ReasonCode.RISING_AMMONIA
                    if param_name == "ammonia"
                    else ReasonCode.SUBOPTIMAL_TEMP
                )
            )
            return ParameterScore(
                parameter=param_name,
                value=value,
                band=HealthStatus.AMBER,
                reason_code=code,
                detail=f"{param_name} is in cautionary amber range ({amber['min']}-{amber['max']})",
            )
    elif "ranges" in amber:
        for r in amber["ranges"]:
            if r["min"] <= value <= r["max"]:
                return ParameterScore(
                    parameter=param_name,
                    value=value,
                    band=HealthStatus.AMBER,
                    reason_code=ReasonCode.SUBOPTIMAL_TEMP
                    if param_name == "temperature"
                    else ReasonCode.SUBOPTIMAL_PH,
                    detail=f"{param_name} is in cautionary amber band ({r['min']}-{r['max']})",
                )

    # 3. Otherwise Red
    red_code = (
        ReasonCode.CRITICAL_LOW_DO
        if param_name == "dissolved_oxygen"
        else (
            ReasonCode.CRITICAL_HIGH_AMMONIA
            if param_name == "ammonia"
            else (
                ReasonCode.CRITICAL_PH_EXTREME
                if param_name == "ph"
                else ReasonCode.CRITICAL_TEMP_EXTREME
            )
        )
    )
    return ParameterScore(
        parameter=param_name,
        value=value,
        band=HealthStatus.RED,
        reason_code=red_code,
        detail=f"{param_name} is outside safe limits in critical RED band",
    )


def compute_linear_trend_slope(
    readings: List[SensorReading],
    param_name: str,
    window_days: int = 7,
    project_days: int = 3,
) -> Optional[TrendFlag]:
    """Calculates linear slope over the window.
    Flags impending breaches within project_days for DO and Ammonia.
    """
    valid_points: List[Tuple[float, float]] = []  # (days_from_start, val)
    if not readings:
        return None

    sorted_readings = sorted(readings, key=lambda r: r.timestamp)
    t0 = sorted_readings[0].timestamp

    for r in sorted_readings:
        v = getattr(r, param_name, None)
        if v is not None:
            days = (r.timestamp - t0).total_seconds() / 86400.0
            valid_points.append((days, float(v)))

    if len(valid_points) < 3:
        return None  # Insufficient points for regression

    x = np.array([p[0] for p in valid_points])
    y = np.array([p[1] for p in valid_points])

    # Filter to only last window_days
    max_day = x.max()
    mask = x >= (max_day - window_days)
    if np.sum(mask) < 3:
        return None

    x_window = x[mask]
    y_window = y[mask]

    slope, intercept = np.polyfit(x_window, y_window, deg=1)
    current_val = y_window[-1]

    # DO trend: negative slope indicates falling oxygen
    if param_name == "dissolved_oxygen" and slope < -0.2:  # Losing > 0.2 mg/L per day
        projected = current_val + (slope * project_days)
        # If currently green (>5.0) and heading to amber/red (<5.0) within project_days
        if current_val >= 5.0 and projected < 5.0:
            days_to_breach = max(0.1, (5.0 - current_val) / slope)
            return TrendFlag(
                parameter=param_name,
                slope_per_day=float(round(slope, 3)),
                current_value=float(round(current_val, 2)),
                projected_days_to_breach=float(round(days_to_breach, 1)),
                warning_code=ReasonCode.FALLING_DO_TREND,
                message=f"Dissolved Oxygen is falling at {abs(slope):.2f} mg/L/day; projected breach in {days_to_breach:.1f} days.",
            )

    # Ammonia trend: positive slope indicates rising toxicity
    if param_name == "ammonia" and slope > 0.02:  # Rising > 0.02 mg/L per day
        projected = current_val + (slope * project_days)
        if current_val <= 0.05 and projected > 0.05:
            days_to_breach = max(0.1, (0.05 - current_val) / slope)
            return TrendFlag(
                parameter=param_name,
                slope_per_day=float(round(slope, 3)),
                current_value=float(round(current_val, 2)),
                projected_days_to_breach=float(round(days_to_breach, 1)),
                warning_code=ReasonCode.RISING_AMMONIA_TREND,
                message=f"Ammonia is rising at {slope:.3f} mg/L/day; projected breach in {days_to_breach:.1f} days.",
            )

    return None
