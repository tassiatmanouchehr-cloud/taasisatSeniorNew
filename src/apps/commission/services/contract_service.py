"""
CommissionContractService — Financial Core PR-A.

The only code that creates/transitions CommissionContract rows. An
organization administrator's edit surface is company_share_percent /
caregiver_share_percent ONLY — propose() resolves platform_share_percent
itself (from CommissionRuleResolver's tier 2-4 chain, the same platform
share already in effect for this company/caregiver pair) and the caller
cannot override it; there is no parameter here that would let a caller set
the platform share to anything else. This is the enforcement Business
Model Section 10 requires ("organization administrator may never modify
Manouchehr's platform share") — structural, not a permission check that
could be bypassed by calling a different code path, because no such path
exists.

Every proposed split must still leave the platform's frozen share intact:
company_share_percent + caregiver_share_percent must equal
100 - platform_share_percent exactly.
"""

import uuid

from django.db import transaction
from django.utils import timezone

from apps.kernel.models.audit import AuditClassification
from apps.kernel.services.audit_service import AuditService
from apps.kernel.services.permission_service import PermissionService

from ..models.contract import OPEN_CONTRACT_STATUSES, CommissionContract, CommissionContractStatus
from ..permission_keys import COMMISSION_CONTRACT_APPROVE, COMMISSION_CONTRACT_PROPOSE, COMMISSION_CONTRACT_TERMINATE
from .cooperation_type import CooperationType
from .errors import ContractError
from .resolver_service import CommissionRuleResolver

SOURCE_MODULE = "M05"


class CommissionContractService:
    @classmethod
    @transaction.atomic
    def propose(
        cls,
        *,
        tenant_id: uuid.UUID,
        company_party_id: uuid.UUID,
        caregiver_party_id: uuid.UUID,
        company_share_percent: int,
        caregiver_share_percent: int,
        reason: str,
        proposed_by=None,
        effective_start=None,
    ) -> CommissionContract:
        PermissionService.require(proposed_by, COMMISSION_CONTRACT_PROPOSE, tenant_id=tenant_id)

        cls._reject_any_open_proposal(
            tenant_id=tenant_id, company_party_id=company_party_id, caregiver_party_id=caregiver_party_id
        )

        platform_rule = CommissionRuleResolver.resolve_service_rule(
            tenant_id=tenant_id,
            cooperation_type=CooperationType.AFFILIATED,
            company_party_id=company_party_id,
            caregiver_party_id=caregiver_party_id,
        )
        platform_share_percent = platform_rule.platform_rate_percent

        proposed_total = company_share_percent + caregiver_share_percent
        required_total = 100 - platform_share_percent
        if proposed_total != required_total:
            raise ContractError(
                f"company_share_percent + caregiver_share_percent must equal "
                f"100 - platform_share_percent ({required_total}); got {proposed_total}. "
                "The platform share cannot be modified through this service.",
            )

        previous_active = cls._active_contract(
            tenant_id=tenant_id,
            company_party_id=company_party_id,
            caregiver_party_id=caregiver_party_id,
        )
        version = (previous_active.version + 1) if previous_active else 1

        contract = CommissionContract.objects.create(
            tenant_id=tenant_id,
            company_party_id=company_party_id,
            caregiver_party_id=caregiver_party_id,
            status=CommissionContractStatus.PENDING_CAREGIVER_APPROVAL,
            platform_share_percent=platform_share_percent,
            company_share_percent=company_share_percent,
            caregiver_share_percent=caregiver_share_percent,
            effective_start=effective_start,
            proposed_by=proposed_by,
            reason=reason,
            version=version,
            supersedes=previous_active,
        )

        AuditService.log(
            tenant_id=tenant_id,
            action="commission.contract.propose",
            resource_type="CommissionContract",
            module_id=SOURCE_MODULE,
            actor_id=getattr(proposed_by, "person_id", None),
            resource_id=contract.id,
            reason=reason,
            audit_class=AuditClassification.FINANCIAL,
            after={
                "company_share_percent": company_share_percent,
                "caregiver_share_percent": caregiver_share_percent,
                "platform_share_percent": platform_share_percent,
                "status": contract.status,
            },
        )

        return contract

    @classmethod
    @transaction.atomic
    def approve(cls, *, contract_id: uuid.UUID, approved_by=None) -> CommissionContract:
        contract = CommissionContract.objects.select_for_update().get(id=contract_id)
        PermissionService.require(approved_by, COMMISSION_CONTRACT_APPROVE, tenant_id=contract.tenant_id)

        if contract.status != CommissionContractStatus.PENDING_CAREGIVER_APPROVAL:
            raise ContractError(f"Cannot approve a contract in '{contract.status}' status.")

        now = timezone.now()
        contract.status = CommissionContractStatus.ACTIVE
        contract.approved_by = approved_by
        contract.approved_at = now
        if contract.effective_start is None:
            contract.effective_start = now
        contract.save(update_fields=["status", "approved_by", "approved_at", "effective_start", "updated_at"])

        if contract.supersedes_id:
            CommissionContract.objects.filter(id=contract.supersedes_id).update(
                status=CommissionContractStatus.SUPERSEDED,
                effective_end=now,
                updated_at=now,
            )

        AuditService.log(
            tenant_id=contract.tenant_id,
            action="commission.contract.approve",
            resource_type="CommissionContract",
            module_id=SOURCE_MODULE,
            actor_id=getattr(approved_by, "person_id", None),
            resource_id=contract.id,
            audit_class=AuditClassification.FINANCIAL,
            after={"status": contract.status, "approved_at": str(contract.approved_at)},
        )

        return contract

    @classmethod
    @transaction.atomic
    def reject(cls, *, contract_id: uuid.UUID, rejected_by=None, reason: str = "") -> CommissionContract:
        contract = CommissionContract.objects.select_for_update().get(id=contract_id)
        PermissionService.require(rejected_by, COMMISSION_CONTRACT_APPROVE, tenant_id=contract.tenant_id)

        if contract.status != CommissionContractStatus.PENDING_CAREGIVER_APPROVAL:
            raise ContractError(f"Cannot reject a contract in '{contract.status}' status.")

        contract.status = CommissionContractStatus.REJECTED
        contract.reason = reason or contract.reason
        contract.save(update_fields=["status", "reason", "updated_at"])

        AuditService.log(
            tenant_id=contract.tenant_id,
            action="commission.contract.reject",
            resource_type="CommissionContract",
            module_id=SOURCE_MODULE,
            actor_id=getattr(rejected_by, "person_id", None),
            resource_id=contract.id,
            reason=reason,
            audit_class=AuditClassification.FINANCIAL,
            after={"status": contract.status},
        )

        return contract

    @classmethod
    @transaction.atomic
    def terminate(cls, *, contract_id: uuid.UUID, terminated_by=None, reason: str = "") -> CommissionContract:
        contract = CommissionContract.objects.select_for_update().get(id=contract_id)
        PermissionService.require(terminated_by, COMMISSION_CONTRACT_TERMINATE, tenant_id=contract.tenant_id)

        if contract.status != CommissionContractStatus.ACTIVE:
            raise ContractError(f"Cannot terminate a contract in '{contract.status}' status.")

        now = timezone.now()
        contract.status = CommissionContractStatus.TERMINATED
        contract.effective_end = now
        contract.reason = reason or contract.reason
        contract.save(update_fields=["status", "effective_end", "reason", "updated_at"])

        AuditService.log(
            tenant_id=contract.tenant_id,
            action="commission.contract.terminate",
            resource_type="CommissionContract",
            module_id=SOURCE_MODULE,
            actor_id=getattr(terminated_by, "person_id", None),
            resource_id=contract.id,
            reason=reason,
            audit_class=AuditClassification.FINANCIAL,
            after={"status": contract.status, "effective_end": str(now)},
        )

        return contract

    # --- internal helpers -------------------------------------------------

    @classmethod
    def _active_contract(cls, *, tenant_id, company_party_id, caregiver_party_id):
        return (
            CommissionContract.objects.filter(
                tenant_id=tenant_id,
                company_party_id=company_party_id,
                caregiver_party_id=caregiver_party_id,
                status=CommissionContractStatus.ACTIVE,
            )
            .order_by("-version")
            .first()
        )

    @classmethod
    def _reject_any_open_proposal(cls, *, tenant_id, company_party_id, caregiver_party_id):
        """At most one open (DRAFT/PENDING_CAREGIVER_APPROVAL) proposal per pair at a time."""
        open_proposal = CommissionContract.objects.filter(
            tenant_id=tenant_id,
            company_party_id=company_party_id,
            caregiver_party_id=caregiver_party_id,
            status__in=OPEN_CONTRACT_STATUSES,
        ).exists()
        if open_proposal:
            raise ContractError(
                "An open (pending) contract proposal already exists for this company/caregiver pair; "
                "resolve it before proposing another.",
            )
