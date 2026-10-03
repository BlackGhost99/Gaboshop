"""Auto-assignment wrapper for delivery workflow."""
import logging

from delivery.assignment_flow import start_delivery_assignment

logger = logging.getLogger(__name__)


def auto_assign_delivery(order):
    """Assign automatically using the assignment flow."""
    try:
        return start_delivery_assignment(order)
    except Exception:
        logger.exception('Erreur auto_assign_delivery')
        return None
