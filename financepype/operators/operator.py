import asyncio
import logging
from abc import abstractmethod

from chronopype.processors.network import NetworkProcessor
from eventspype.pub.multipublisher import MultiPublisher
from pydantic import BaseModel

from financepype.constants import get_instance_id
from financepype.operators.nonce_creator import NonceCreator
from financepype.platforms.platform import Platform


class OperatorConfiguration(BaseModel):
    platform: Platform


class Operator:
    """Base class for platform operators.

    An operator represents a connection to a trading platform or blockchain,
    providing a standardized interface for interacting with different platforms.
    Each operator maintains its own platform-specific state and identifiers.

    Attributes:
        _platform (Platform): The platform this operator connects to
        _microseconds_nonce_provider (NonceCreator): Generator for unique operation IDs
        _client_instance_id (str): Unique identifier for this client instance

    Example:
        >>> platform = Platform("binance")
        >>> operator = Operator(platform)
        >>> print(operator.name)  # Output: "binance"
    """

    def __init__(self, configuration: OperatorConfiguration):
        """Initialize a new operator.

        Args:
            configuration (OperatorConfiguration): The configuration for the operator
        """
        super().__init__()

        self._configuration = configuration

        self._microseconds_nonce_provider = NonceCreator.for_microseconds()
        self._client_instance_id = get_instance_id()

        self._event_publishing = MultiPublisher()

    @classmethod
    @abstractmethod
    def logger(cls) -> logging.Logger:
        raise NotImplementedError

    @property
    def configuration(self) -> OperatorConfiguration:
        return self._configuration

    @property
    def platform(self) -> Platform:
        """Get the platform this operator connects to.

        Returns:
            object: The platform instance
        """
        return self.configuration.platform

    @property
    def name(self) -> str:
        """Get the name of this operator.

        Returns:
            str: The platform name
        """
        return str(self.platform)

    @property
    def display_name(self) -> str:
        """Get a human-readable name for this operator.

        Returns:
            str: The display name
        """
        return self.name

    @property
    @abstractmethod
    def current_timestamp(self) -> float:
        raise NotImplementedError

    @property
    def publishing(self) -> MultiPublisher:
        return self._event_publishing


class OperatorProcessor(NetworkProcessor):
    def __init__(self, operator: Operator):
        super().__init__()

        self._operator = operator
        self._poll_notifier = asyncio.Event()

    # === Loops ===

    async def update_loop(self, interval_seconds: float):
        while True:
            try:
                await self._poll_notifier.wait()

                await self._update_loop_fetch_updates()

                self._last_poll_timestamp = self.state.last_timestamp
                self._poll_notifier.clear()
            except asyncio.CancelledError:
                raise
            except NotImplementedError:
                raise
            except Exception:
                self.logger().error(
                    "Unexpected error while fetching exchange updates.",
                    exc_info=True,
                )
                await self._sleep(0.5)

    @abstractmethod
    async def _update_loop_fetch_updates(self) -> None:
        raise NotImplementedError

    async def _sleep(self, seconds: float) -> None:
        """
        Sleeps for a given number of seconds.
        """
        await asyncio.sleep(seconds)
