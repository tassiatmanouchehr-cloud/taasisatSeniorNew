"""
NotificationProviderRegistry — in-process map of channel -> provider.

Mirrors apps.jobs.registry.JobRegistry's shape: exactly one provider per
channel. Providers register themselves from
apps.notifications.providers.fake.register_providers(), called from
NotificationsConfig.ready().
"""

import logging
from typing import TYPE_CHECKING, Protocol

from apps.notifications.errors import NotificationsError

if TYPE_CHECKING:
    from apps.notifications.dto import DeliveryResult
    from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationProvider(Protocol):
    """Structural interface every provider adapter implements."""

    name: str

    def send(self, notification: "Notification") -> "DeliveryResult":
        ...


class NotificationProviderRegistry:
    """Central, in-memory registry of channel -> provider."""

    _providers: dict[str, NotificationProvider] = {}

    @classmethod
    def register(cls, channel: str, provider: NotificationProvider) -> None:
        cls._providers[channel] = provider
        logger.debug("Registered provider %r for channel %s", provider, channel)

    @classmethod
    def get_provider(cls, channel: str) -> NotificationProvider:
        provider = cls._providers.get(channel)
        if provider is None:
            raise NotificationsError(f"no provider registered for channel {channel!r}")
        return provider

    @classmethod
    def is_registered(cls, channel: str) -> bool:
        return channel in cls._providers

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations. Intended for test isolation only."""
        cls._providers.clear()
