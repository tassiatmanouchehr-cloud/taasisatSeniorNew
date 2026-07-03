# CES Kernel Envelope

## Standard Event Envelope
```json
{
  "event_id": "evt_...",
  "event_type": "Module.Entity.Action.v1",
  "event_version": "1.0",
  "occurred_at": "ISO-8601",
  "published_at": "ISO-8601",
  "tenant_id": "...",
  "source_module": "ModuleXX",
  "source_entity": {
    "id": "...",
    "entity_type": "..."
  },
  "actor": {},
  "correlation_id": "...",
  "causation_id": "...",
  "idempotency_key": "...",
  "schema_ref": "...",
  "payload": {},
  "privacy_class": "public|internal|restricted|sensitive",
  "audit_class": "none|standard|financial|security|compliance"
}
```

## Event Rules
- Events are immutable facts.
- Event names must be past tense.
- Events must not contain internal database rows.
- Breaking payload changes require a new event version.
- Consumers must tolerate unknown fields.
- Producers must not remove required fields from a frozen version.
