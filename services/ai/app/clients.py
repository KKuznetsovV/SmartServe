"""Thin HTTP clients for the other backend services this orchestrator calls into to
execute confirmed AI actions — ai owns no data of its own (see
docs/microservices-plan.md §4), so every mutation is a REST call to the owning service,
with the caller's JWT forwarded for that service's own authorization checks.
"""

from http_client import ServiceClient

from app.core.config import settings

auth_client = ServiceClient(settings.AUTH_SERVICE_URL)
catalog_client = ServiceClient(settings.CATALOG_SERVICE_URL)
printing_client = ServiceClient(settings.PRINTING_SERVICE_URL)
reporting_client = ServiceClient(settings.REPORTING_SERVICE_URL)
staff_client = ServiceClient(settings.STAFF_SERVICE_URL)
