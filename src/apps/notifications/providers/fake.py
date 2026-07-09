"""
Fake/internal provider adapters — Module 21 foundation.

No network calls, no real credentials. Each provider simulates a delivery
outcome and returns a structured DeliveryResult. Default behavior is
deterministic success; pass always_fail=True to simulate a provider that
never succeeds (used to exercise the retry/dead-letter path in tests).
"""

import uuid

from apps.notifications.dto import DeliveryResult
from apps.notifications.models import NotificationChannel
from apps.notifications.providers.registry import NotificationProviderRegistry


class _FakeProvider:
    """Base fake provider: always succeeds unless always_fail is set."""

    name = "fake"

    def __init__(self, *, always_fail: bool = False):
        self.always_fail = always_fail

    def send(self, notification) -> DeliveryResult:
        if self.always_fail:
            return DeliveryResult(success=False, provider_name=self.name, message="simulated delivery failure")
        return DeliveryResult(
            success=True, provider_name=self.name, message="simulated delivery success",
            external_id=str(uuid.uuid4()),
        )


class FakeSmsProvider(_FakeProvider):
    name = "fake-sms"


class FakeEmailProvider(_FakeProvider):
    name = "fake-email"


class FakePushProvider(_FakeProvider):
    name = "fake-push"


class FakeInAppProvider(_FakeProvider):
    name = "fake-in-app"


def register_providers() -> None:
    """Idempotently register the default fake provider for every channel."""
    NotificationProviderRegistry.register(NotificationChannel.SMS, FakeSmsProvider())
    NotificationProviderRegistry.register(NotificationChannel.EMAIL, FakeEmailProvider())
    NotificationProviderRegistry.register(NotificationChannel.PUSH, FakePushProvider())
    NotificationProviderRegistry.register(NotificationChannel.IN_APP, FakeInAppProvider())
