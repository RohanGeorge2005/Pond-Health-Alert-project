from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from datetime import datetime, timezone
import uuid


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Pond(Base):
    __tablename__ = "ponds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), default="Tilapia")  # Tilapia, Carp, Freshwater Prawn
    area_sq_meters: Mapped[float] = mapped_column(Float, default=1000.0)
    farmer_phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    location_district: Mapped[str] = mapped_column(String(50), default="Dakshina Kannada")  # Coastal Karnataka
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    devices: Mapped[list["IoTDevice"]] = relationship("IoTDevice", back_populates="pond", cascade="all, delete-orphan")
    readings: Mapped[list["PondReading"]] = relationship("PondReading", back_populates="pond", cascade="all, delete-orphan")
    daily_checks: Mapped[list["PondDailyCheck"]] = relationship("PondDailyCheck", back_populates="pond", cascade="all, delete-orphan")
    photos: Mapped[list["PondPhoto"]] = relationship("PondPhoto", back_populates="pond", cascade="all, delete-orphan")
    alerts: Mapped[list["PondAlert"]] = relationship("PondAlert", back_populates="pond", cascade="all, delete-orphan")


class IoTDevice(Base):
    __tablename__ = "iot_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    device_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)  # e.g., "ESP32-POND-01"
    pond_id: Mapped[str] = mapped_column(String(36), ForeignKey("ponds.id", ondelete="CASCADE"), index=True, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # SHA-256 or token hash
    hardware_model: Mapped[str] = mapped_column(String(50), default="ESP32-WROOM-32D")
    firmware_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    sampling_interval_seconds: Mapped[int] = mapped_column(Integer, default=120)  # Configurable 60 - 300s
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    battery_level_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0 - 100%
    signal_rssi: Mapped[int | None] = mapped_column(Integer, nullable=True)  # dBm, e.g. -65
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(String(30), default="OFFLINE")  # "ONLINE", "OFFLINE", "DEGRADED"
    sensor_health_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # per-sensor probe status
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pond: Mapped["Pond"] = relationship("Pond", back_populates="devices")
    readings: Mapped[list["PondReading"]] = relationship("PondReading", back_populates="device")


class PondReading(Base):
    __tablename__ = "readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)  # Client or Device UUID
    pond_id: Mapped[str] = mapped_column(String(36), ForeignKey("ponds.id", ondelete="CASCADE"), index=True, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("iot_devices.device_id", ondelete="SET NULL"), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    dissolved_oxygen: Mapped[float | None] = mapped_column(Float, nullable=True)
    turbidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    conductivity: Mapped[float | None] = mapped_column(Float, nullable=True)
    ammonia: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_level_cm: Mapped[float | None] = mapped_column(Float, nullable=True)  # Optional water level
    battery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="iot_sensor")  # "iot_sensor", "manual", "replay_sim"
    client_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pond: Mapped["Pond"] = relationship("Pond", back_populates="readings")
    device: Mapped["IoTDevice | None"] = relationship("IoTDevice", back_populates="readings")


class PondDailyCheck(Base):
    __tablename__ = "daily_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    pond_id: Mapped[str] = mapped_column(String(36), ForeignKey("ponds.id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    feeding: Mapped[str] = mapped_column(String(20), nullable=False)  # normal, less, none
    behavior: Mapped[str] = mapped_column(String(20), nullable=False)  # normal, gasping, slow, at_surface
    dead_fish_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pond: Mapped["Pond"] = relationship("Pond", back_populates="daily_checks")


class PondPhoto(Base):
    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    pond_id: Mapped[str] = mapped_column(String(36), ForeignKey("ponds.id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
    passed_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    gate_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # blur score, brightness, foreground
    predicted_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    gradcam_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    pond: Mapped["Pond"] = relationship("Pond", back_populates="photos")


class PondAlert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    pond_id: Mapped[str] = mapped_column(String(36), ForeignKey("ponds.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # green, amber, red, cant_tell
    severity: Mapped[str] = mapped_column(String(20), default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False)
    message_en: Mapped[str] = mapped_column(Text, nullable=False)
    message_kn: Mapped[str] = mapped_column(Text, nullable=False)
    actions_en: Mapped[list | None] = mapped_column(JSON, nullable=True)
    actions_kn: Mapped[list | None] = mapped_column(JSON, nullable=True)
    delivery_channels: Mapped[list] = mapped_column(JSON, default=list)  # ["dashboard", "sms", "voice"]
    delivery_status: Mapped[str] = mapped_column(String(30), default="DELIVERED")  # PENDING, DELIVERED, FAILED
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pond: Mapped["Pond"] = relationship("Pond", back_populates="alerts")
