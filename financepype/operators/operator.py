import asyncio
import time

from chronopype.processors.network import NetworkProcessor

from financepype.constants import get_instance_id
from financepype.operators.nonce_creator import NonceCreator
from financepype.platforms.platform import Platform


class Operator(NetworkProcessor):
    def __init__(self, platform: Platform):
        super().__init__()

        self._platform = platform
        self._microseconds_nonce_provider = NonceCreator.for_microseconds()
        self._client_instance_id = get_instance_id()

    @property
    def platform(self) -> object:
        return self._platform

    @property
    def name(self) -> str:
        return str(self.platform)

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def status_dict(self) -> dict[str, bool]:
        return {}

    @property
    def ready(self) -> bool:
        """
        Returns True if the connector is ready to operate (all connections established with the exchange). If it is
        not ready it returns False.
        """
        return all(self.status_dict.values())

    @property
    def current_timestamp(self) -> float:
        return (
            self.state.last_timestamp
            if self.state.last_timestamp is not None
            else self._time()
        )

    def _time(self) -> float:
        """
        Method created to enable tests to mock the machine time
        :return: The machine time (time.time())
        """
        return time.time()

    async def _sleep(self, delay: float) -> None:
        """
        Method created to enable tests to prevent processes from sleeping
        """
        await asyncio.sleep(delay)
