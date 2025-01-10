class OrderBookError(Exception):
    """Base class for order book errors."""


class OrderBookEmptyError(OrderBookError):
    """Exception raised when the order book is empty."""
