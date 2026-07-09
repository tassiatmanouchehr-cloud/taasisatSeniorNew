"""Delivery result DTO — Module 21 foundation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryResult:
    """Structured result returned by a provider's send() call."""

    success: bool
    provider_name: str
    message: str = ""
    external_id: str | None = None
