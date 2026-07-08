"""
Regression tests: PaymentTransaction must be append-only at the model
level — creation works normally, but existing rows can never be modified
or deleted, mirroring LedgerEntry/WalletTransaction.
"""

from decimal import Decimal

from apps.finance.models import PaymentTransaction
from apps.finance.services import PaymentService

from .helpers import FinanceTestCase


class PaymentTransactionImmutabilityTest(FinanceTestCase):
    def _payment(self):
        from apps.finance.services import FinancialPartyService

        payer = FinancialPartyService.resolve_party_for_customer(self.customer_profile)
        receiver = FinancialPartyService.resolve_party_for_supplier(self.supplier)
        return PaymentService.record_payment(
            payer_party_id=payer.id,
            receiver_party_id=receiver.id,
            amount=Decimal("1000"),
            payment_method="CASH",
        )

    def test_creation_still_works_normally(self):
        payment = self._payment()
        self.assertIsNotNone(payment.pk)
        self.assertTrue(PaymentTransaction.objects.filter(id=payment.id).exists())

    def test_existing_payment_cannot_be_modified(self):
        payment = PaymentTransaction.objects.get(id=self._payment().id)

        payment.amount = Decimal("999999")
        with self.assertRaises(ValueError):
            payment.save()

        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal("1000"))

    def test_existing_payment_cannot_be_modified_even_with_update_fields(self):
        payment = PaymentTransaction.objects.get(id=self._payment().id)

        payment.status = "FAILED"
        with self.assertRaises(ValueError):
            payment.save(update_fields=["status"])

    def test_existing_payment_cannot_be_deleted(self):
        payment = PaymentTransaction.objects.get(id=self._payment().id)

        with self.assertRaises(ValueError):
            payment.delete()

        self.assertTrue(PaymentTransaction.objects.filter(id=payment.id).exists())
