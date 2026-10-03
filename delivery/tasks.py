from celery import shared_task
from orders.models import Order

from delivery.assignment_flow import (
    assign_next_driver,
    broadcast_if_unaccepted,
    handle_assignment_timeout,
    start_delivery_assignment,
)


@shared_task
def assign_nearest_delivery_agent(order_id):
    """Assign the nearest available delivery agent via the assignment flow."""
    order = Order.objects.filter(id=order_id).first()
    if not order:
        return "Order not found"
    delivery = start_delivery_assignment(order)
    if not delivery:
        return "Assignment not started"
    return f"Assignment started for delivery {delivery.id}"


@shared_task
def assignment_timeout_check(delivery_id, assignment_round):
    handle_assignment_timeout(delivery_id, assignment_round)
    return "timeout_checked"


@shared_task
def broadcast_delivery_if_unaccepted(delivery_id):
    broadcast_if_unaccepted(delivery_id)
    return "broadcast_checked"


@shared_task
def retry_delivery_assignment(delivery_id):
    assign_next_driver(delivery_id, reason='retry')
    return "retry_triggered"
