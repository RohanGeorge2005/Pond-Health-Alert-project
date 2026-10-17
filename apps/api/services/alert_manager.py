import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from apps.api.domain.models import HealthStatus, ReasonCode

logger = logging.getLogger("AlertManager")


class AlertManager:
    """Manages automatic alert deduplication, cooldowns, and multi-channel delivery.
    Ensures farmers are not spammed with duplicate alerts every 1-2 minutes for the same
    unresolved state, while ensuring critical alerts are never silently suppressed.
    """

    def __init__(self, cooldown_minutes: int = 30):
        self.cooldown_minutes = cooldown_minutes
        # Key: (pond_id, reason_code) -> last_alerted_at
        self._last_alert_times: Dict[str, datetime] = {}

    def should_emit_alert(self, pond_id: str, status: HealthStatus, reason_codes: List[ReasonCode], now: Optional[datetime] = None) -> bool:
        if now is None:
            now = datetime.now(timezone.utc)

        # GREEN never requires an emergency alert emission
        if status == HealthStatus.GREEN:
            return False

        # Critical RED alerts have shorter cooldown (10 min) or immediate re-trigger if new reason
        cooldown = timedelta(minutes=10 if status == HealthStatus.RED else self.cooldown_minutes)

        should_emit = False
        for code in reason_codes:
            key = f"{pond_id}:{code.value}"
            last_time = self._last_alert_times.get(key)
            if last_time is None or (now - last_time) > cooldown:
                should_emit = True
                self._last_alert_times[key] = now

        return should_emit

    def reset_cooldown(self, pond_id: str):
        """Clears cooldown when pond returns to GREEN."""
        keys_to_del = [k for k in self._last_alert_times if k.startswith(f"{pond_id}:")]
        for k in keys_to_del:
            del self._last_alert_times[k]
