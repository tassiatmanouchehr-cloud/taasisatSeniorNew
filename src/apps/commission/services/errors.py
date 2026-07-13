class CommissionError(Exception):
    """Base error for apps.commission service-layer failures."""


class InvalidPolicyError(CommissionError):
    """A commission rule payload failed validation (shares don't sum to 100, etc.)."""


class ContractError(CommissionError):
    """A CommissionContract lifecycle operation was attempted from an invalid state."""


class SnapshotError(CommissionError):
    """A CommissionSnapshot could not be created or resolved."""


class DeadlineError(CommissionError):
    """A PaymentDeadline lifecycle operation was attempted from an invalid state."""


class PreServicePaymentError(CommissionError):
    """Financial Core PR-B: pre-service invoice/PaymentIntent creation failed."""


class ObjectionPeriodError(CommissionError):
    """Financial Core PR-B: an ObjectionPeriod lifecycle operation was attempted from an invalid state."""


class DisputeError(CommissionError):
    """Financial Core PR-B: a Dispute lifecycle operation was attempted from an invalid state."""


class ExecutionPaymentGuardError(CommissionError):
    """Financial Core PR-B: execution was attempted without a valid paid Escrow."""
