"""HTTP clients for services ordering calls (device lookup for KDS/display sockets)."""

from smartserve_shared.http_client import ServiceClient

from app.core.config import settings

auth_client = ServiceClient(settings.AUTH_SERVICE_URL)
