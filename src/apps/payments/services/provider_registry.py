"""PaymentProviderRegistry — Module 15 foundation. Maps a provider name to its adapter class."""

from ..models import PaymentProvider
from ..providers.fake import FakePaymentProviderAdapter
from .errors import PaymentError


class PaymentProviderRegistry:
    """Resolves the adapter class registered for a given PaymentProvider value."""

    _adapters = {
        PaymentProvider.FAKE: FakePaymentProviderAdapter,
    }

    @classmethod
    def get_adapter(cls, provider: str):
        try:
            return cls._adapters[provider]
        except KeyError:
            raise PaymentError(f"No payment provider adapter registered for '{provider}'.")
