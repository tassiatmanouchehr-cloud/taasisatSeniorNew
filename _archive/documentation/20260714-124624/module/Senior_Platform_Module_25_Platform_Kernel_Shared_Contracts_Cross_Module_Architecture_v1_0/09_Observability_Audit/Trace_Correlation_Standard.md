# Trace & Correlation Standard

## Required Correlation Fields
- correlation_id: end-to-end request or workflow trace.
- causation_id: direct cause of current action.
- idempotency_key: duplicate prevention for critical operations.
- trace_id: distributed tracing identifier.
- span_id: current operation identifier.

## Rules
- All cross-module operations must propagate correlation_id.
- Events produced from commands must reference causation_id.
- User-facing errors must include correlation_id.
- Background jobs must preserve initiating correlation context.
