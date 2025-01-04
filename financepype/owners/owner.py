import logging
from decimal import Decimal
from typing import Any, cast

from chronopype.processors.network import NetworkProcessor

from financepype.assets.asset import Asset
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.assets.factory import AssetFactory
from financepype.constants import s_decimal_0
from financepype.markets.position import Position
from financepype.owners.owner_id import OwnerIdentifier
from financepype.platforms.platform import Platform
from financepype.simulations.balances.tracking.tracker import (
    BalanceTracker,
    BalanceType,
)


class Owner(NetworkProcessor):
    _logger: logging.Logger | None = None

    def __init__(self, identifier: OwnerIdentifier):
        super().__init__()

        self._identifier = identifier

        self._balance_tracker = BalanceTracker()

    @classmethod
    def logger(cls) -> logging.Logger:
        if cls._logger is None:
            cls._logger = logging.getLogger("user")
        return cls._logger

    # === Properties ===

    @property
    def identifier(self) -> OwnerIdentifier:
        return self._identifier

    @property
    def name(self) -> str:
        return self.identifier.name

    @property
    def platform(self) -> Platform:
        return self.identifier.platform

    @property
    def balance_tracker(self) -> BalanceTracker:
        return self._balance_tracker

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

    # === Balances Management ===

    def get_available_balance(self, currency: str) -> Decimal:
        asset = AssetFactory.get_asset(self.platform, currency)
        return self.balance_tracker.get_balance(asset, BalanceType.AVAILABLE)

    def get_all_available_balances(self) -> dict[str, Decimal]:
        return {
            asset.identifier.value: amount
            for asset, amount in self.balance_tracker.available_balances.items()
        }

    def get_all_balances(self) -> dict[str, Decimal]:
        return {
            asset.identifier.value: amount
            for asset, amount in self.balance_tracker.total_balances.items()
        }

    def get_balance(self, currency: str) -> Decimal:
        asset = AssetFactory.get_asset(self.platform, currency)
        self.logger().debug(
            f"[Owner:GetBalance] Getting balance for {currency} (asset={asset}, platform={self.platform}, asset_hash={hash(asset)})"
        )
        balance = self.balance_tracker.get_balance(asset, BalanceType.TOTAL)
        self.logger().debug(f"[Owner:GetBalance] Balance for {currency} is {balance}")
        self.logger().debug(
            f"[Owner:GetBalance] Total balances: {self.balance_tracker._total_balances}"
        )
        return balance

    def set_balances(
        self,
        total_balances: list[tuple[Asset, Decimal]],
        available_balances: list[tuple[Asset, Decimal]],
        complete_snapshot: bool = False,
        **kwargs: Any,
    ) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
        self.logger().debug(
            f"[Owner:SetBalances] Setting balances for platform {self.platform}:"
        )
        for asset, amount in total_balances:
            self.logger().debug(
                f"  Total balance: {amount} of {asset} (hash={hash(asset)})"
            )
        for asset, amount in available_balances:
            self.logger().debug(
                f"  Available balance: {amount} of {asset} (hash={hash(asset)})"
            )

        total_balance_changes = self.balance_tracker.set_balances(
            total_balances,
            "Set Balances",
            BalanceType.TOTAL,
            complete_snapshot,
        )
        available_balance_changes = self.balance_tracker.set_balances(
            available_balances,
            "Set Balances",
            BalanceType.AVAILABLE,
            complete_snapshot,
        )

        self.logger().debug(
            f"[Owner:SetBalances] Total balances after update: {self.balance_tracker._total_balances}"
        )
        self.logger().debug(
            f"[Owner:SetBalances] Available balances after update: {self.balance_tracker._available_balances}"
        )

        updated_total_balances = {}
        for balance_change in total_balance_changes:
            if balance_change.amount == s_decimal_0:
                continue
            updated_total_balances[balance_change.asset.identifier.value] = (
                self.balance_tracker.get_balance(
                    balance_change.asset, BalanceType.TOTAL
                )
            )

        updated_available_balances = {}
        for balance_change in available_balance_changes:
            if balance_change.amount == s_decimal_0:
                continue
            updated_available_balances[balance_change.asset.identifier.value] = (
                self.balance_tracker.get_balance(
                    balance_change.asset, BalanceType.AVAILABLE
                )
            )

        if updated_total_balances or updated_available_balances:
            self.logger().debug(
                f"[Owner:SetBalances] New Total Balances: {updated_total_balances}"
            )
            self.logger().debug(
                f"[Owner:SetBalances] New Available Balances: {updated_available_balances}"
            )

        return updated_total_balances, updated_available_balances

    # === Positions Management ===

    def get_position(self, trading_pair: str, side: DerivativeSide) -> Position | None:
        """
        Returns an active position if exists, otherwise returns None
        """
        asset = cast(
            DerivativeContract,
            AssetFactory.get_asset(self.platform, trading_pair, side=side),
        )
        return self.balance_tracker.get_position(asset)

    def get_all_positions(self) -> dict[DerivativeContract, Position]:
        """
        Returns all active positions if exists
        """
        return self.balance_tracker.positions

    def set_position(self, position: Position) -> None:
        self.balance_tracker.set_position(position, "Set Position", BalanceType.TOTAL)
        self.balance_tracker.set_position(
            position, "Set Position", BalanceType.AVAILABLE
        )

    def remove_position(
        self, trading_pair: str, side: DerivativeSide
    ) -> Position | None:
        asset = cast(
            DerivativeContract,
            AssetFactory.get_asset(self.platform, trading_pair, side=side),
        )
        return self.balance_tracker.remove_position(asset)
