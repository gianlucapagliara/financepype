from typing import cast

from financepype.operations.orders.tracker import OrderTracker
from financepype.owners.owner import Owner, OwnerConfiguration, OwnerIdentifier
from financepype.platforms.centralized import CentralizedPlatform


class AccountIdentifier(OwnerIdentifier):
    platform: CentralizedPlatform
    name: str

    @property
    def identifier(self) -> str:
        return f"{self.platform.identifier}:{self.name}"


class AccountConfiguration(OwnerConfiguration):
    pass


class Account(Owner):
    def __init__(
        self,
        configuration: AccountConfiguration,
    ) -> None:
        super().__init__(configuration)

        self._order_tracker = OrderTracker(event_publishers=[self])

    @property
    def identifier(self) -> AccountIdentifier:
        return cast(AccountIdentifier, super().identifier)

    @property
    def name(self) -> str:
        return self.identifier.name
