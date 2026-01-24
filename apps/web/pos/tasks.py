"""
POS background tasks - order submission with retry logic.

These functions are designed to work with Celery but can also be called
synchronously for development/demo purposes.

When Celery is configured, convert these to @shared_task decorators.
"""

import logging
from typing import Any

from apps.web.pos.services import (
    OrderSubmissionError,
    handle_pos_submission_failure,
    submit_order_to_pos,
)

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [60, 120, 300]  # Seconds between retries: 1min, 2min, 5min


def submit_order_to_pos_task(
    order_id: int,
    retry_count: int = 0,
    _sync_mode: bool = True,
) -> dict[str, Any]:
    """
    Submit order to POS with retry logic.

    In production with Celery, this would be:
    @shared_task(bind=True, max_retries=3, default_retry_delay=60, retry_backoff=True)
    def submit_order_to_pos_task(self, order_id: int):
        ...

    Args:
        order_id: ID of the Order to submit.
        retry_count: Current retry attempt (0-indexed).
        _sync_mode: If True (default), runs synchronously. Set False for testing.

    Returns:
        Dict with submission result or error info.
    """
    try:
        result = submit_order_to_pos(order_id)
        logger.info(
            "Order %s submitted to POS successfully: %s",
            order_id,
            result,
        )
        return {
            "success": True,
            "order_id": order_id,
            "external_id": result.get("external_id"),
            "confirmation_code": result.get("confirmation_code"),
        }

    except OrderSubmissionError as e:
        if e.is_retryable and retry_count < MAX_RETRIES:
            # Schedule retry
            delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
            logger.warning(
                "Order %s submission failed (attempt %d/%d), will retry in %ds: %s",
                order_id,
                retry_count + 1,
                MAX_RETRIES,
                delay,
                e.message,
            )

            # In Celery, this would be:
            # raise self.retry(exc=e, countdown=delay)

            # For sync mode, we could sleep and retry, but that's not
            # ideal for request handling. Instead, return a "pending" status
            # and let the caller decide whether to retry.
            return {
                "success": False,
                "order_id": order_id,
                "error": e.message,
                "is_retryable": True,
                "retry_count": retry_count,
                "next_retry_delay": delay,
            }
        else:
            # Max retries exceeded or non-retryable error
            logger.error(
                "Order %s submission permanently failed after %d attempts: %s",
                order_id,
                retry_count + 1,
                e.message,
            )
            handle_pos_submission_failure(order_id, e.message, auto_refund=False)

            return {
                "success": False,
                "order_id": order_id,
                "error": e.message,
                "is_retryable": False,
                "status": "pos_failed",
            }

    except Exception as e:
        # Unexpected error
        logger.exception("Unexpected error submitting order %s: %s", order_id, e)
        return {
            "success": False,
            "order_id": order_id,
            "error": str(e),
            "is_retryable": False,
        }


def retry_failed_order(order_id: int) -> dict[str, Any]:
    """
    Retry a failed order submission.

    Called from admin or API to manually retry orders that failed
    POS submission.

    Args:
        order_id: ID of the Order to retry.

    Returns:
        Dict with submission result.
    """
    from apps.web.restaurant.models import Order  # noqa: PLC0415

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return {
            "success": False,
            "error": f"Order {order_id} not found",
        }

    if order.status != "pos_failed":
        return {
            "success": False,
            "error": f"Order is not in pos_failed state (current: {order.status})",
        }

    # Reset status for retry
    order.status = "confirmed"
    order.save(update_fields=["status"])

    logger.info("Retrying POS submission for order %s", order_id)

    return submit_order_to_pos_task(order_id, retry_count=0)


# NOTE: For Celery integration, create @shared_task wrapper around
# submit_order_to_pos_task with bind=True, max_retries=3, retry_backoff=True.
