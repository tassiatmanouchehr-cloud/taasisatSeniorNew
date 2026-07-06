"""
Health check endpoint.

Returns the health status of the platform including database and cache connectivity.
No authentication required — this endpoint is for load balancers and monitoring.
"""

import logging

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)


class HealthCheckView(View):
    """
    GET /api/v1/health/

    Returns 200 if all dependencies are healthy, 503 otherwise.
    Response includes correlation_id from middleware.
    """

    def get(self, request):
        health = {
            "status": "healthy",
            "db": self._check_db(),
            "cache": self._check_cache(),
            "correlation_id": getattr(request, "correlation_id", None),
        }

        # If any dependency is unhealthy, return 503
        if health["db"] != "ok" or health["cache"] != "ok":
            health["status"] = "unhealthy"
            status_code = 503
        else:
            status_code = 200

        return JsonResponse(health, status=status_code)

    def _check_db(self):
        """Verify database connectivity with a simple query."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return "ok"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return f"error: {type(e).__name__}"

    def _check_cache(self):
        """Verify Redis/cache connectivity with a set/get cycle."""
        try:
            cache.set("_health_check", "ok", timeout=10)
            value = cache.get("_health_check")
            if value == "ok":
                return "ok"
            return "error: unexpected value"
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return f"error: {type(e).__name__}"
