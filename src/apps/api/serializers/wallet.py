"""DRF serializers for the read-only Wallet endpoints — Module 17B. No mutation shapes here."""

from rest_framework import serializers


class WalletBalanceSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()


class WalletTransactionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    transaction_type = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance_after = serializers.DecimalField(max_digits=14, decimal_places=2)
    reason = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
