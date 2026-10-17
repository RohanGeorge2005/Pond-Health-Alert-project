import enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class HealthStatus(str, enum.Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    CANT_TELL = "cant_tell"


class ReasonCode(str, enum.Enum):
    # Data Quality Issues -> CANT_TELL
    MISSING_CRITICAL_READINGS = "MISSING_CRITICAL_READINGS"
    STALE_DATA = "STALE_DATA"
    PHYSICALLY_IMPOSSIBLE_VALUE = "PHYSICALLY_IMPOSSIBLE_VALUE"
    EXCESSIVE_SENSOR_DROPOUT = "EXCESSIVE_SENSOR_DROPOUT"
    UNCERTAIN_PHOTO_PREDICTION = "UNCERTAIN_PHOTO_PREDICTION"
    PHOTO_FAILED_QUALITY_GATE = "PHOTO_FAILED_QUALITY_GATE"
    SENSOR_DEVICE_OFFLINE = "SENSOR_DEVICE_OFFLINE"
    SENSOR_PROBE_MALFUNCTION = "SENSOR_PROBE_MALFUNCTION"

    # Red Conditions
    CRITICAL_LOW_DO = "CRITICAL_LOW_DO"
    CRITICAL_HIGH_AMMONIA = "CRITICAL_HIGH_AMMONIA"
    CRITICAL_PH_EXTREME = "CRITICAL_PH_EXTREME"
    CRITICAL_TEMP_EXTREME = "CRITICAL_TEMP_EXTREME"
    HIGH_FISH_MORTALITY = "HIGH_FISH_MORTALITY"
    CONFIRMED_DISEASE_SYMPTOMS = "CONFIRMED_DISEASE_SYMPTOMS"
    MULTIPLE_AMBER_PARAMETERS = "MULTIPLE_AMBER_PARAMETERS"
    AMBER_WITH_RISING_MORTALITY = "AMBER_WITH_RISING_MORTALITY"

    # Amber Conditions
    LOW_DO = "LOW_DO"
    RISING_AMMONIA = "RISING_AMMONIA"
    FALLING_DO_TREND = "FALLING_DO_TREND"
    RISING_AMMONIA_TREND = "RISING_AMMONIA_TREND"
    SUBOPTIMAL_TEMP = "SUBOPTIMAL_TEMP"
    SUBOPTIMAL_PH = "SUBOPTIMAL_PH"
    SUBOPTIMAL_TURBIDITY = "SUBOPTIMAL_TURBIDITY"
    SUBOPTIMAL_CONDUCTIVITY = "SUBOPTIMAL_CONDUCTIVITY"
    SUDDEN_TEMP_JUMP = "SUDDEN_TEMP_JUMP"
    REDUCED_FEEDING = "REDUCED_FEEDING"
    ABNORMAL_BEHAVIOR = "ABNORMAL_BEHAVIOR"
    SUSPECTED_DISEASE = "SUSPECTED_DISEASE"

    # Green Conditions
    OPTIMAL_WATER_QUALITY = "OPTIMAL_WATER_QUALITY"
    NORMAL_FISH_OBSERVATION = "NORMAL_FISH_OBSERVATION"


class FeedingBehavior(str, enum.Enum):
    NORMAL = "normal"
    LESS = "less"
    NONE = "none"


class FishBehavior(str, enum.Enum):
    NORMAL = "normal"
    GASPING = "gasping"
    SLOW = "slow"
    AT_SURFACE = "at_surface"


class SensorReading(BaseModel):
    reading_id: Optional[str] = None
    pond_id: str
    device_id: Optional[str] = None
    timestamp: datetime
    temperature: Optional[float] = None
    ph: Optional[float] = None
    dissolved_oxygen: Optional[float] = None
    turbidity: Optional[float] = None
    conductivity: Optional[float] = None
    ammonia: Optional[float] = None
    water_level_cm: Optional[float] = None
    battery_pct: Optional[float] = None
    is_simulated: bool = False
    source: str = "iot_sensor"  # "iot_sensor", "manual", "replay_sim"


class DeviceStatus(BaseModel):
    device_id: str
    pond_id: str
    hardware_model: str = "ESP32-WROOM-32D"
    firmware_version: str = "1.0.0"
    is_online: bool = True
    last_seen_at: datetime
    battery_level_pct: Optional[float] = 95.0
    signal_rssi: Optional[int] = -65  # dBm
    sensor_health: Dict[str, str] = Field(default_factory=lambda: {
        "dissolved_oxygen": "OK",
        "ph": "OK",
        "temperature": "OK",
        "ammonia": "OK",
    })


class DailyCheck(BaseModel):
    check_id: Optional[str] = None
    pond_id: str
    timestamp: datetime
    feeding: FeedingBehavior
    behavior: FishBehavior
    dead_fish_count: int = Field(ge=0)
    notes: Optional[str] = None


class PhotoInferenceResult(BaseModel):
    photo_id: Optional[str] = None
    pond_id: str
    timestamp: datetime
    passed_gate: bool
    gate_failure_reasons: List[str] = Field(default_factory=list)
    predicted_class: Optional[str] = None
    confidence: Optional[float] = None
    is_uncertain: bool = False
    gradcam_url: Optional[str] = None


class TrendFlag(BaseModel):
    parameter: str
    slope_per_day: float
    current_value: float
    projected_days_to_breach: Optional[float] = None
    warning_code: ReasonCode
    message: str


class ParameterScore(BaseModel):
    parameter: str
    value: Optional[float] = None
    band: HealthStatus  # green, amber, red, or cant_tell
    reason_code: Optional[ReasonCode] = None
    detail: str


class DataQualitySummary(BaseModel):
    is_valid: bool
    stale_hours: Optional[float] = None
    device_offline: bool = False
    impossible_values: List[str] = Field(default_factory=list)
    outliers_detected: List[str] = Field(default_factory=list)
    missing_critical: List[str] = Field(default_factory=list)
    data_source_type: str = "iot_sensor"  # "iot_sensor", "manual", "simulated", "synthetic"


class AssessmentResult(BaseModel):
    pond_id: str
    assessment_time: datetime
    status: HealthStatus
    reason_codes: List[ReasonCode]
    explanation_en: str
    explanation_kn: str
    actions_en: List[str]
    actions_kn: List[str]
    parameter_scores: Dict[str, ParameterScore]
    trend_warnings: List[TrendFlag] = Field(default_factory=list)
    data_quality: DataQualitySummary
    device_status: Optional[DeviceStatus] = None
    reviewed_thresholds: bool = False
