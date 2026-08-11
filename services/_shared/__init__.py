"""services/_shared — small internal-only library imported by path from every backend service.

Contains only:
- security.py  — JWT verification (shared secret/algorithm, no per-request call to `auth`)
- http_client.py — thin httpx wrapper for service-to-service REST calls
- events.py    — Redis pub/sub publish/subscribe helpers

Deliberately minimal: no service mesh, no circuit breakers, no distributed tracing.
"""
