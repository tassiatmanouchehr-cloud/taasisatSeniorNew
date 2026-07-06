"""
Correlation ID middleware.

Ensures every request has a unique correlation_id for distributed tracing.
If the client provides X-Correlation-ID header, it is reused; otherwise generated.
The correlation_id is attached to the request object and included in the response.
"""

import uuid


class CorrelationMiddleware:
    """
    Middleware that assigns a correlation ID to every request.

    - Reads X-Correlation-ID from incoming request headers
    - Generates a new UUID if not provided
    - Attaches to request.correlation_id
    - Includes in response as X-Correlation-ID header
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Read from header or generate new
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Attach to request for use in views, services, logging
        request.correlation_id = correlation_id

        # Process request
        response = self.get_response(request)

        # Include in response
        response["X-Correlation-ID"] = correlation_id

        return response
