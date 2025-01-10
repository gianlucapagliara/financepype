import time


class NonceCreator:
    """Generator for unique, monotonically increasing nonce values.

    This class generates unique nonce values based on timestamps with configurable
    precision. It ensures that generated nonces are always increasing, even if
    called with the same timestamp multiple times.

    The class supports three precision levels:
    - Seconds (1 unit precision)
    - Milliseconds (1000 units precision)
    - Microseconds (1000000 units precision)

    Attributes:
        SECONDS_PRECISION (int): Multiplier for seconds precision
        MILLISECONDS_PRECISION (int): Multiplier for milliseconds precision
        MICROSECONDS_PRECISION (int): Multiplier for microseconds precision

    Example:
        >>> creator = NonceCreator.for_milliseconds()
        >>> nonce1 = creator.get_tracking_nonce()  # e.g., 1641234567000
        >>> nonce2 = creator.get_tracking_nonce()  # e.g., 1641234567001
    """

    SECONDS_PRECISION = 1
    MILLISECONDS_PRECISION = 1000
    MICROSECONDS_PRECISION = 1000000

    def __init__(self, precision: int):
        """Initialize a nonce creator with specified precision.

        Args:
            precision (int): The precision multiplier for timestamps
        """
        self._precision = int(precision)
        self._last_tracking_nonce = 0

    @classmethod
    def for_seconds(cls) -> "NonceCreator":
        """Create a nonce generator with seconds precision.

        Returns:
            NonceCreator: A new instance with seconds precision
        """
        return cls(precision=cls.SECONDS_PRECISION)

    @classmethod
    def for_milliseconds(cls) -> "NonceCreator":
        """Create a nonce generator with milliseconds precision.

        Returns:
            NonceCreator: A new instance with milliseconds precision
        """
        return cls(precision=cls.MILLISECONDS_PRECISION)

    @classmethod
    def for_microseconds(cls) -> "NonceCreator":
        """Create a nonce generator with microseconds precision.

        Returns:
            NonceCreator: A new instance with microseconds precision
        """
        return cls(precision=cls.MICROSECONDS_PRECISION)

    def get_tracking_nonce(self, timestamp: float | int | None = None) -> int:
        """Generate a unique tracking nonce.

        This method generates a unique nonce based on the provided timestamp
        or current time. It ensures that each nonce is greater than the last,
        even if called with the same timestamp.

        Args:
            timestamp (float | int | None): Optional timestamp to base nonce on

        Returns:
            int: A unique, monotonically increasing nonce value
        """
        nonce_candidate = int((timestamp or self._time()) * self._precision)
        self._last_tracking_nonce = (
            nonce_candidate
            if nonce_candidate > self._last_tracking_nonce
            else self._last_tracking_nonce + 1
        )
        return self._last_tracking_nonce

    @staticmethod
    def _time() -> float:
        """Get the current time.

        This method is separated to allow mocking in tests without
        affecting the system time.

        Returns:
            float: Current Unix timestamp
        """
        return time.time()
