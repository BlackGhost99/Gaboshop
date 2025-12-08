"""Project-level services package.

This package contains shared services (notifications, location, etc.)
used by multiple apps. Implementations are intentionally lightweight
stubs to be expanded later.
"""

from .notification_service import NotificationService
from .location_service import LocationService

__all__ = [
    'NotificationService',
    'LocationService',
]
