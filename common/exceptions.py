from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
import logging

logger = logging.getLogger(__name__)

class InsufficientStockException(APIException):
    """
    Raised when an order requests more stock than currently available.
    Returns HTTP 409 Conflict.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Insufficient stock available for one or more requested products.'
    default_code = 'insufficient_stock'

    def __init__(self, detail=None, product_id=None, sku=None, requested=None, available=None):
        if detail is None and sku is not None:
            detail = (
                f"Insufficient stock for product '{sku}' (ID: {product_id}). "
                f"Requested: {requested}, Available: {available}."
            )
        super().__init__(detail=detail)


class InvalidOrderStateException(APIException):
    """
    Raised when an invalid order transition is attempted (e.g. cancelling a cancelled order).
    Returns HTTP 409 Conflict.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Invalid order state transition.'
    default_code = 'invalid_order_state'


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler to ensure standard responses and proper logging.
    """
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exceptions
        logger.exception("Unhandled server exception: %s", exc)
        return None

    return response
