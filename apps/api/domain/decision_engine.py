from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from apps.api.domain.models import (
    SensorReading,
    DailyCheck,
    PhotoInferenceResult,
    HealthStatus,
    ReasonCode,
    AssessmentResult,
    ParameterScore,
    DataQualitySummary,
    FeedingBehavior,
    FishBehavior,
)
from apps.api.domain.water_rules import (
    validate_reading_physics,
    check_stale_data,
    evaluate_parameter_band,
    compute_linear_trend_slope,
)


def evaluate_pond_health(
    pond_id: str,
    latest_reading: Optional[SensorReading],
    historical_readings: List[SensorReading],
    daily_check: Optional[DailyCheck],
    photo_result: Optional[PhotoInferenceResult],
    bands_config: Dict[str, Any],
    now: Optional[datetime] = None,
) -> AssessmentResult:
    """Pure Decision Engine Function.
    
    Precedence rules:
    1. Data problems (missing, stale >48h, physically impossible) -> CANT_TELL (NEVER FALSE GREEN)
    2. Any red input -> RED
    3. >= 2 ambers OR (rising dead fish count with any amber) -> RED
    4. Any amber -> AMBER
    5. Photo gate failed or uncertain -> CANT_TELL or AMBER, NEVER GREEN if photo was submitted
    6. Optimal water + normal daily check + (healthy/no photo) -> GREEN
    """
    if now is None:
        now = datetime.now(timezone.utc)

    reason_codes: List[ReasonCode] = []
    actions_en: List[str] = []
    actions_kn: List[str] = []
    param_scores: Dict[str, ParameterScore] = {}
    trend_warnings = []

    # 1. Check Missing Reading
    if latest_reading is None:
        return AssessmentResult(
            pond_id=pond_id,
            assessment_time=now,
            status=HealthStatus.CANT_TELL,
            reason_codes=[ReasonCode.MISSING_CRITICAL_READINGS],
            explanation_en="No water readings available for this pond.",
            explanation_kn="ಈ ಕೊಳಕ್ಕೆ ಯಾವುದೇ ನೀರಿನ ಗುಣಮಟ್ಟದ ಮಾಪನಗಳು ಲಭ್ಯವಿಲ್ಲ.",
            actions_en=["Test water parameters immediately using test kit.", "Contact local fisheries officer."],
            actions_kn=["ಪರೀಕ್ಷಾ ಕಿಟ್ ಬಳಸಿ ತಕ್ಷಣ ನೀರಿನ ಪರೀಕ್ಷೆ ನಡೆಸಿ.", "ಸ್ಥಳೀಯ ಮೀನುಗಾರಿಕಾ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ."],
            parameter_scores={},
            trend_warnings=[],
            data_quality=DataQualitySummary(
                is_valid=False,
                missing_critical=["temperature", "ph", "dissolved_oxygen"],
            ),
            reviewed_thresholds=False,
        )

    # 2. Check Physical Possibility
    is_physical, physical_violations = validate_reading_physics(latest_reading, bands_config)
    if not is_physical:
        return AssessmentResult(
            pond_id=pond_id,
            assessment_time=now,
            status=HealthStatus.CANT_TELL,
            reason_codes=[ReasonCode.PHYSICALLY_IMPOSSIBLE_VALUE],
            explanation_en=f"Sensor reported impossible values: {'; '.join(physical_violations)}",
            explanation_kn="ಸೆನ್ಸರ್ ಅಸಾಧ್ಯವಾದ ಮೌಲ್ಯಗಳನ್ನು ವರದಿ ಮಾಡಿದೆ. ಮರುಪರೀಕ್ಷಿಸಿ.",
            actions_en=["Recalibrate water sensors immediately.", "Inspect probes for debris or fouling."],
            actions_kn=["ಸೆನ್ಸರ್ ಪ್ರೋಬ್‌ಗಳನ್ನು ಸ್ವಚ್ಛಗೊಳಿಸಿ ಮತ್ತು ಮರು-ಕ್ಯಾಲಿಬ್ರೇಟ್ ಮಾಡಿ."],
            parameter_scores={},
            trend_warnings=[],
            data_quality=DataQualitySummary(
                is_valid=False,
                impossible_values=physical_violations,
            ),
            reviewed_thresholds=False,
        )

    # 3. Check Stale Data (> 48 hours)
    stale_hours_cfg = bands_config.get("metadata", {}).get("stale_data_threshold_hours", 48.0)
    is_stale, elapsed_hours = check_stale_data(latest_reading.timestamp, now, stale_hours_cfg)
    if is_stale:
        return AssessmentResult(
            pond_id=pond_id,
            assessment_time=now,
            status=HealthStatus.CANT_TELL,
            reason_codes=[ReasonCode.STALE_DATA],
            explanation_en=f"Water data is stale ({elapsed_hours:.1f} hours old, limit {stale_hours_cfg}h). Fresh readings required.",
            explanation_kn=f"ನೀರಿನ ಡೇಟಾ ಹಳೆಯದಾಗಿದೆ ({elapsed_hours:.1f} ಗಂಟೆಗಳು ಹಳೆಯದು). ಹೊಸ ಪರೀಕ್ಷೆ ಅಗತ್ಯವಿದೆ.",
            actions_en=["Take a fresh water sample reading right away."],
            actions_kn=["ತಕ್ಷಣ ತಾಜಾ ನೀರಿನ ಮಾದರಿ ಪರೀಕ್ಷೆಯನ್ನು ದಾಖಲಿಸಿ."],
            parameter_scores={},
            trend_warnings=[],
            data_quality=DataQualitySummary(
                is_valid=False,
                stale_hours=elapsed_hours,
            ),
            reviewed_thresholds=False,
        )

    # 4. Check Critical Missing Readings (DO, Temp, pH must be present)
    critical_params = ["temperature", "ph", "dissolved_oxygen"]
    missing_crit = [p for p in critical_params if getattr(latest_reading, p, None) is None]
    if missing_crit:
        return AssessmentResult(
            pond_id=pond_id,
            assessment_time=now,
            status=HealthStatus.CANT_TELL,
            reason_codes=[ReasonCode.MISSING_CRITICAL_READINGS],
            explanation_en=f"Critical parameters missing: {', '.join(missing_crit)}.",
            explanation_kn=f"ಮುಖ್ಯ ಮಾಪನಗಳು ಕಾಣೆಯಾಗಿವೆ: {', '.join(missing_crit)}.",
            actions_en=["Provide all essential test-kit readings (DO, pH, Temp)."],
            actions_kn=["ಎಲ್ಲಾ ಪ್ರಮುಖ ಪರೀಕ್ಷಾ ಫಲಿತಾಂಶಗಳನ್ನು ಒದಗಿಸಿ (DO, pH, ತಾಪಮಾನ)."],
            parameter_scores={},
            trend_warnings=[],
            data_quality=DataQualitySummary(
                is_valid=False,
                missing_critical=missing_crit,
            ),
            reviewed_thresholds=False,
        )

    # 5. Evaluate Parameter Bands
    red_count = 0
    amber_count = 0
    params_cfg = bands_config.get("parameters", {})

    for param, cfg in params_cfg.items():
        val = getattr(latest_reading, param, None)
        score = evaluate_parameter_band(param, val, cfg)
        param_scores[param] = score
        if score.band == HealthStatus.RED:
            red_count += 1
            if score.reason_code and score.reason_code not in reason_codes:
                reason_codes.append(score.reason_code)
        elif score.band == HealthStatus.AMBER:
            amber_count += 1
            if score.reason_code and score.reason_code not in reason_codes:
                reason_codes.append(score.reason_code)

    # 6. Trend Flag Calculations (DO & Ammonia)
    window_days = bands_config.get("metadata", {}).get("trend_window_days", 7)
    all_readings = historical_readings + [latest_reading]

    do_trend = compute_linear_trend_slope(all_readings, "dissolved_oxygen", window_days)
    if do_trend:
        trend_warnings.append(do_trend)
        amber_count += 1
        if do_trend.warning_code not in reason_codes:
            reason_codes.append(do_trend.warning_code)

    nh3_trend = compute_linear_trend_slope(all_readings, "ammonia", window_days)
    if nh3_trend:
        trend_warnings.append(nh3_trend)
        amber_count += 1
        if nh3_trend.warning_code not in reason_codes:
            reason_codes.append(nh3_trend.warning_code)

    # 7. Evaluate Daily Check
    has_mortality = False
    if daily_check:
        if daily_check.dead_fish_count > 5:
            red_count += 1
            has_mortality = True
            reason_codes.append(ReasonCode.HIGH_FISH_MORTALITY)
        elif daily_check.dead_fish_count > 0:
            amber_count += 1
            has_mortality = True
            reason_codes.append(ReasonCode.AMBER_WITH_RISING_MORTALITY)

        if daily_check.behavior in (FishBehavior.GASPING, FishBehavior.AT_SURFACE):
            amber_count += 1
            reason_codes.append(ReasonCode.ABNORMAL_BEHAVIOR)

        if daily_check.feeding == FeedingBehavior.NONE:
            amber_count += 1
            reason_codes.append(ReasonCode.REDUCED_FEEDING)

    # 8. Evaluate Photo Gate and Inference Result
    photo_uncertain = False
    if photo_result:
        if not photo_result.passed_gate:
            # Gate failure cannot upgrade to green and prompts retake
            photo_uncertain = True
            reason_codes.append(ReasonCode.PHOTO_FAILED_QUALITY_GATE)
        elif photo_result.is_uncertain:
            photo_uncertain = True
            reason_codes.append(ReasonCode.UNCERTAIN_PHOTO_PREDICTION)
        elif photo_result.predicted_class and photo_result.predicted_class != "healthy":
            if photo_result.confidence and photo_result.confidence >= 0.70:
                red_count += 1
                reason_codes.append(ReasonCode.CONFIRMED_DISEASE_SYMPTOMS)
            else:
                amber_count += 1
                reason_codes.append(ReasonCode.SUSPECTED_DISEASE)

    # 9. Aggregate Status Determination
    # Rule: Any red input -> RED
    if red_count > 0:
        final_status = HealthStatus.RED
    # Rule: >= 2 ambers or (rising dead fish with any amber) -> RED
    elif amber_count >= 2 or (has_mortality and amber_count >= 1):
        final_status = HealthStatus.RED
        if amber_count >= 2 and ReasonCode.MULTIPLE_AMBER_PARAMETERS not in reason_codes:
            reason_codes.append(ReasonCode.MULTIPLE_AMBER_PARAMETERS)
    # Rule: Single amber or photo uncertain when otherwise green -> AMBER
    elif amber_count == 1:
        final_status = HealthStatus.AMBER
    elif photo_uncertain:
        # Photo failed gate or uncertain: cannot be green!
        final_status = HealthStatus.AMBER
    else:
        # Green only if strictly optimal across the board
        final_status = HealthStatus.GREEN
        reason_codes.append(ReasonCode.OPTIMAL_WATER_QUALITY)

    # 10. Generate Explanations and Actions (Bilingual)
    reasons_str = " + ".join([r.value for r in reason_codes])

    if final_status == HealthStatus.RED:
        explanation_en = f"Pond in critical condition: {reasons_str}."
        explanation_kn = f"ಕೊಳ ಅಪಾಯದ ಸ್ಥಿತಿಯಲ್ಲಿದೆ: {reasons_str}. ತುರ್ತು ಕ್ರಮ ಅಗತ್ಯ."
        actions_en = [
            "Start aerators immediately to raise dissolved oxygen.",
            "Cease all fish feeding until parameters normalize.",
            "Contact Taluk Fisheries Extension Officer.",
        ]
        actions_kn = [
            "ಆಮ್ಲಜನಕ ಹೆಚ್ಚಿಸಲು ತಕ್ಷಣ ಏರೇಟರ್‌ಗಳನ್ನು ಚಾಲೂ ಮಾಡಿ.",
            "ಪರಿಸ್ಥಿತಿ ಸುಧಾರಿಸುವವರೆಗೆ ಮೀನಿಗೆ ಆಹಾರ ನೀಡುವುದನ್ನು ನಿಲ್ಲಿಸಿ.",
            "ತಾಲೂಕು ಮೀನುಗಾರಿಕಾ ವಿಸ್ತರಣಾ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        ]
    elif final_status == HealthStatus.AMBER:
        explanation_en = f"Pond requires caution: {reasons_str}."
        explanation_kn = f"ಕೊಳ ಎಚ್ಚರಿಕೆಯ ಸ್ಥಿತಿಯಲ್ಲಿದೆ: {reasons_str}."
        actions_en = [
            "Monitor water dissolved oxygen and temperature every 4 hours.",
            "Reduce feeding rate by 50%.",
            "Prepare backup aeration if cloud cover persists.",
        ]
        actions_kn = [
            "ಪ್ರತಿ 4 ಗಂಟೆಗಳಿಗೊಮ್ಮೆ ನೀರಿನ ಆಮ್ಲಜನಕ ಮತ್ತು ತಾಪಮಾನ ಪರಿಶೀಲಿಸಿ.",
            "ಆಹಾರದ ಪ್ರಮಾಣವನ್ನು 50% ಕಡಿಮೆ ಮಾಡಿ.",
            "ಮೋಡ ಕವಿದ ವಾತಾವರಣವಿದ್ದರೆ ಹೆಚ್ಚುವರಿ ಏರೇಶನ್ ಸಿದ್ಧಪಡಿಸಿ.",
        ]
    else:
        explanation_en = "Pond conditions are optimal. Water quality and fish observations normal."
        explanation_kn = "ಕೊಳದ ಸ್ಥಿತಿ ಉತ್ತಮವಾಗಿದೆ. ನೀರಿನ ಗುಣಮಟ್ಟ ಮತ್ತು ಮೀನುಗಳ ಚಟುವಟಿಕೆ ಸಾಮಾನ್ಯವಾಗಿದೆ."
        actions_en = [
            "Maintain standard feeding schedule.",
            "Continue routine daily water parameter checks.",
        ]
        actions_kn = [
            "ನಿಗದಿತ ಆಹಾರ ನೀಡುವ ವೇಳಾಪಟ್ಟಿಯನ್ನು ಮುಂದುವರಿಸಿ.",
            "ದೈನಂದಿನ ನೀರಿನ ತಪಾಸಣೆಯನ್ನು ಮುಂದುವರಿಸಿ.",
        ]

    data_quality = DataQualitySummary(
        is_valid=True,
        stale_hours=elapsed_hours,
        data_source_type="simulated" if latest_reading.is_simulated else "real",
    )

    return AssessmentResult(
        pond_id=pond_id,
        assessment_time=now,
        status=final_status,
        reason_codes=reason_codes,
        explanation_en=explanation_en,
        explanation_kn=explanation_kn,
        actions_en=actions_en,
        actions_kn=actions_kn,
        parameter_scores=param_scores,
        trend_warnings=trend_warnings,
        data_quality=data_quality,
        reviewed_thresholds=False,
    )
