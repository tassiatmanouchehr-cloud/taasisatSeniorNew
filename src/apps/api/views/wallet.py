"""
Wallet endpoints — Module 17B. Read-only, no mutations.

All persistence access stays inside apps.wallet.services — this view never
touches Wallet/WalletTransaction models directly. GET /api/v1/wallet/balance/
deliberately calls WalletService.get_wallet_or_none() rather than
create_wallet()/get_or_create_wallet() (both writes) since a GET must never
have a side effect. If no wallet row exists yet, a zero balance is returned
without creating one.
"""

from rest_framework.response import Response

from apps.finance.services import FinancialPartyService
from apps.wallet.services import WalletConfiguration, WalletService, WalletTransactionService

from ..pagination import paginate, parse_pagination_params
from ..permission_keys import WALLET_READ
from ..permissions import require_permission, resolve_customer_profile
from ..serializers import WalletBalanceSerializer, WalletTransactionSerializer
from .base import ApiView


def _resolve_wallet(request):
    customer_profile = resolve_customer_profile(request)
    party = FinancialPartyService.resolve_party_for_customer(customer_profile)
    return WalletService.get_wallet_or_none(party=party)


class WalletBalanceView(ApiView):
    """GET /api/v1/wallet/balance/ — the authenticated customer's own wallet balance."""

    def get(self, request):
        tenant_id = require_permission(request, WALLET_READ)
        wallet = _resolve_wallet(request)

        if wallet is None:
            data = {"balance": "0.00", "currency": WalletConfiguration.get_default_currency(tenant_id=tenant_id)}
        else:
            data = {"balance": WalletService.get_balance(wallet), "currency": wallet.currency}

        return Response(WalletBalanceSerializer(data).data)


class WalletTransactionListView(ApiView):
    """GET /api/v1/wallet/transactions/ — the authenticated customer's own transaction history."""

    def get(self, request):
        require_permission(request, WALLET_READ)
        wallet = _resolve_wallet(request)
        limit, offset = parse_pagination_params(request.query_params)

        items = WalletTransactionService.list_transactions(wallet) if wallet is not None else ()

        page = paginate(items, limit=limit, offset=offset)
        serializer = WalletTransactionSerializer(page.results, many=True)
        return Response(
            {
                "results": serializer.data,
                "limit": page.limit,
                "offset": page.offset,
                "total_count": page.total_count,
                "has_more": page.has_more,
            }
        )
