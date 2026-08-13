"""services/_shared — small internal-only library imported by path from every backend service.

Contains only:
- security.py  — JWT verification (shared secret/algorithm, no per-request call to `auth`)
- http_client.py — thin httpx wrapper for service-to-service REST calls

Deliberately minimal: no service mesh, no circuit breakers, no distributed tracing. The
cross-service event bus (RabbitMQ) is NOT part of this shared library — each participating
service has its own `app/core/mq.py` copy, following this codebase's established convention
of duplicating small infra helpers rather than growing this package (see docs/microservices-plan.md §4).
"""
