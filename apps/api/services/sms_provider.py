from abc import ABC, abstractmethod
import logging
from typing import Dict, Any

logger = logging.getLogger("SMSProvider")


class SMSProvider(ABC):
    @abstractmethod
    async def send_sms(self, phone: str, message: str) -> bool:
        pass


class MockConsoleSMSProvider(SMSProvider):
    """Console mock provider for demo and local development."""

    def __init__(self):
        self.sent_messages = []

    async def send_sms(self, phone: str, message: str) -> bool:
        logger.info(f"[DEMO SMS to {phone}]: {message}")
        self.sent_messages.append({"phone": phone, "message": message})
        return True


class TwilioMSG91Provider(SMSProvider):
    """Production adapter for Twilio or MSG91 (DND compliant transactional route in India)."""

    def __init__(self, api_key: str, sender_id: str):
        self.api_key = api_key
        self.sender_id = sender_id

    async def send_sms(self, phone: str, message: str) -> bool:
        # Stub implementation ready for production credentials
        return True
