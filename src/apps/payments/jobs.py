"""
Settlement recovery job — Epic 03 Sprint 1 remediation (Critical Finding 1).

If SettlementOrchestrationService.settle_payment_intent() raises when
triggered synchronously from PaymentCallbackService.process_callback(),
the PaymentIntent is left SUCCEEDED with no PaymentTransaction/LedgerEntry/
WalletTransaction — and, without this module, no durable record that
settlement still needs to happen. This reuses the existing apps.jobs
foundation (Module 20/22) rather than inventing a new retry mechanism:
JobService.enqueue() is idempotent (unique_together on
(tenant_id, job_type, idempotency_key), database-enforced), and
run_due_jobs already provides exponential backoff + dead-lettering after
max_retries with zero new code here.

The handler itself does nothing but re-invoke settle_payment_intent(),
which is independently idempotent (see settlement_orchestration_service's
own existing_payment short-circuit) — safe to run any number of times,
including after a prior partial attempt.

Registered from PaymentsConfig.ready(), mirroring the
apps.jobs.handlers.register_handlers()/apps.kernel.events.handlers
registration pattern already established in this repository.
"""

import logging

from apps.jobs.registry import JobRegistry

logger = logging.getLogger(__name__)

PAYMENT_SETTLEMENT_RETRY = "payments.settlement.retry"


def _retry_settlement(job) -> None:
    """Re-attempt settlement for the PaymentIntent named in job.payload.

    Raises on failure (uncaught) so JobService.execute_job() records it as a
    failed JobRun and reschedules via the standard backoff/dead-letter path
    — this function must not swallow exceptions itself.
    """
    from .services.settlement_orchestration_service import SettlementOrchestrationService

    payment_intent_id = job.payload["payment_intent_id"]
    SettlementOrchestrationService.settle_payment_intent(payment_intent_id=payment_intent_id)


def register_handlers() -> None:
    """Idempotently register this app's job handlers."""
    JobRegistry.register(PAYMENT_SETTLEMENT_RETRY, _retry_settlement)
