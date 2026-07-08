"""ReportingService — Module 16 foundation. Thin facade over the four category-specific services."""

import uuid

from ..dto import FinancialSummaryReport, MarketplaceStatsReport, OrderCountsReport, ProviderPerformanceReport
from .financial_report_service import FinancialReportService
from .marketplace_report_service import MarketplaceReportService
from .operational_report_service import OperationalReportService
from .provider_report_service import ProviderReportService


class ReportingService:
    """Single import surface for all Module 16 reports."""

    @classmethod
    def get_order_counts(cls, tenant_id: uuid.UUID) -> OrderCountsReport:
        return OperationalReportService.get_order_counts(tenant_id)

    @classmethod
    def get_provider_report(cls, tenant_id: uuid.UUID, supplier_id: uuid.UUID) -> ProviderPerformanceReport:
        return ProviderReportService.get_report_for_supplier(tenant_id, supplier_id)

    @classmethod
    def list_provider_reports(cls, tenant_id: uuid.UUID) -> tuple[ProviderPerformanceReport, ...]:
        return ProviderReportService.list_reports(tenant_id)

    @classmethod
    def get_financial_summary(cls, tenant_id: uuid.UUID) -> FinancialSummaryReport:
        return FinancialReportService.get_financial_summary(tenant_id)

    @classmethod
    def get_marketplace_stats(cls, tenant_id: uuid.UUID) -> MarketplaceStatsReport:
        return MarketplaceReportService.get_marketplace_stats(tenant_id)
