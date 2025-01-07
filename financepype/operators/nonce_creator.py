import time


class NonceCreator:
    SECONDS_PRECISION = 1
    MILLISECONDS_PRECISION = 1000
    MICROSECONDS_PRECISION = 1000000

    def __init__(self, precision: int):
        self._precision = int(precision)
        self._last_tracking_nonce = 0

    @classmethod
    def for_seconds(cls) -> "NonceCreator":
        return cls(precision=cls.SECONDS_PRECISION)

    @classmethod
    def for_milliseconds(cls) -> "NonceCreator":
        return cls(precision=cls.MILLISECONDS_PRECISION)

    @classmethod
    def for_microseconds(cls) -> "NonceCreator":
        return cls(precision=cls.MICROSECONDS_PRECISION)

    def get_tracking_nonce(self, timestamp: float | int | None = None) -> int:
        """
        Returns a unique number based on the timestamp provided as parameter or the machine time
        :params timestamp: The timestamp to use as the base for the nonce. If not provided the current time will be used.
        :return: the generated nonce
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
        """Mocked in test cases without affecting system `time.time()`."""
        return time.time()
