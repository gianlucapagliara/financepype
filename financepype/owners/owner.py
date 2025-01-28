import asyncio
import logging
from abc import abstractmethod
from decimal import Decimal
from typing import Any, cast

from eventspype.pub.multipublisher import MultiPublisher
from pydantic import BaseModel, ConfigDict, Field

from financepype.assets.asset import Asset
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.assets.factory import AssetFactory
from financepype.constants import s_decimal_0
from financepype.markets.position import Position
from financepype.markets.trading_pair import TradingPair
from financepype.platforms.platform import Platform
from financepype.simulations.balances.tracking.tracker import (
    BalanceTracker,
    BalanceType,
)


class OwnerIdentifier(BaseModel):
    """Unique identifier for trading account owners.

    This class represents a unique identifier for trading account owners
    across different platforms. It combines a platform-specific name with
    the platform identifier to ensure uniqueness.

    The identifier is immutable and can be safely used as a dictionary key
    or in sets. It implements proper equality and hashing behavior.

    Attributes:
        name (str): Platform-specific owner name
        platform (Platform): The platform this owner belongs to
        identifier (str): Combined unique identifier (platform:name)

    Example:
        >>> platform = Platform(identifier="binance")
        >>> owner = OwnerIdentifier(name="trader1", platform=platform)
        >>> print(owner.identifier)  # Outputs: binance:trader1
        >>> owners = {owner}  # Can be used in sets
    """

    model_config = ConfigDict(frozen=True)

    platform: Platform = Field(description="The platform the owner belongs to")

    @property
    @abstractmethod
    def identifier(self) -> str:
        """Get the unique identifier string.

        The identifier combines the platform identifier and owner name
        in the format "platform:name".

        Returns:
            str: The combined unique identifier
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        """Get the string representation of the owner identifier.

        Returns:
            str: A human-readable representation of the owner
        """
        return f"<Owner: {self.identifier}>"


class NamedOwnerIdentifier(OwnerIdentifier):
    """An owner identifier with a name."""

    name: str = Field(description="The name of the owner")

    @property
    def identifier(self) -> str:
        return f"{self.platform.identifier}:{self.name}"


class OwnerConfiguration(BaseModel):
    """Configuration for trading account owners.

    This class defines the configuration parameters required to initialize
    a trading account owner. It uses Pydantic for validation.

    Attributes:
        identifier (OwnerIdentifier): Unique identifier for the owner
    """

    identifier: OwnerIdentifier


class Owner(MultiPublisher):
    """Base class for trading account owners.

    This class represents a trading account owner and provides functionality
    for managing balances and positions across different trading platforms.
    It maintains a balance tracker for monitoring available and total balances
    of different assets.

    Attributes:
        _logger (logging.Logger | None): Logger instance for the owner
        _configuration (OwnerConfiguration): Owner configuration
        _balance_tracker (BalanceTracker): Tracks asset balances
        _balances_ready (asyncio.Event): Event signaling balance initialization

    Example:
        >>> config = OwnerConfiguration(identifier=owner_id)
        >>> owner = Owner(config)
        >>> balance = owner.get_balance("BTC")
        >>> positions = owner.get_all_positions()
    """

    _logger: logging.Logger | None = None

    def __init__(self, configuration: OwnerConfiguration):
        """Initialize a new owner.

        Args:
            configuration (OwnerConfiguration): Owner configuration
        """
        super().__init__()

        self._configuration = configuration

        self._balance_tracker = BalanceTracker()
        self._balances_ready = asyncio.Event()

    @classmethod
    def logger(cls) -> logging.Logger:
        """Get the logger instance.

        Returns:
            logging.Logger: The logger for this owner
        """
        if cls._logger is None:
            cls._logger = logging.getLogger("user")
        return cls._logger

    def __repr__(self) -> str:
        """Get string representation of the owner.

        Returns:
            str: Human-readable representation
        """
        return f"<{self.__class__.__name__}: {self.identifier.identifier}>"

    # === Properties ===

    @property
    def identifier(self) -> OwnerIdentifier:
        """Get the owner's unique identifier.

        Returns:
            OwnerIdentifier: The owner identifier
        """
        return self._configuration.identifier

    @property
    def platform(self) -> Platform:
        """Get the owner's trading platform.

        Returns:
            Platform: The trading platform
        """
        return self.identifier.platform

    @property
    def balance_tracker(self) -> BalanceTracker:
        """Get the balance tracker.

        Returns:
            BalanceTracker: The balance tracker instance
        """
        return self._balance_tracker

    @property
    @abstractmethod
    def current_timestamp(self) -> float:
        raise NotImplementedError

    # === Balances Management ===

    def get_available_balance(self, currency: str) -> Decimal:
        """Get available balance for a currency.

        Args:
            currency (str): Currency identifier

        Returns:
            Decimal: Available balance amount
        """
        asset = AssetFactory.get_asset(self.platform, currency)
        return self.balance_tracker.get_balance(asset, BalanceType.AVAILABLE)

    def get_all_available_balances(self) -> dict[str, Decimal]:
        """Get all available balances.

        Returns:
            dict[str, Decimal]: Map of currency to available balance
        """
        return {
            asset.identifier.value: amount
            for asset, amount in self.balance_tracker.available_balances.items()
        }

    def get_all_balances(self) -> dict[str, Decimal]:
        """Get all total balances.

        Returns:
            dict[str, Decimal]: Map of currency to total balance
        """
        return {
            asset.identifier.value: amount
            for asset, amount in self.balance_tracker.total_balances.items()
        }

    def get_balance(self, currency: str) -> Decimal:
        """Get total balance for a currency.

        Args:
            currency (str): Currency identifier

        Returns:
            Decimal: Total balance amount
        """
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
        """Set total and available balances.

        This method updates both total and available balances for multiple
        assets at once. It can either update specific balances or provide
        a complete snapshot of all balances.

        Args:
            total_balances (list[tuple[Asset, Decimal]]): List of (asset, amount) pairs for total balances
            available_balances (list[tuple[Asset, Decimal]]): List of (asset, amount) pairs for available balances
            complete_snapshot (bool): Whether this is a complete balance snapshot
            **kwargs: Additional arguments

        Returns:
            tuple[dict[str, Decimal], dict[str, Decimal]]: Updated total and available balances
        """
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
        """Get an active position for a trading pair.

        Args:
            trading_pair (str): The trading pair
            side (DerivativeSide): Position side (long/short)

        Returns:
            Position | None: The active position or None if not found
        """
        asset = cast(
            DerivativeContract,
            AssetFactory.get_asset(self.platform, trading_pair, side=side),
        )
        return self.balance_tracker.get_position(asset)

    def get_all_positions(self) -> dict[DerivativeContract, Position]:
        """Get all active positions.

        Returns:
            dict[DerivativeContract, Position]: Map of contracts to positions
        """
        return self.balance_tracker.positions

    def set_position(self, position: Position) -> None:
        """Set a position.

        Args:
            position (Position): The position to set
        """
        self.balance_tracker.set_position(position, "Set Position", BalanceType.TOTAL)
        self.balance_tracker.set_position(
            position, "Set Position", BalanceType.AVAILABLE
        )

    def remove_position(
        self, trading_pair: TradingPair, side: DerivativeSide
    ) -> Position | None:
        """Remove a position.

        Args:
            trading_pair (TradingPair): The trading pair
            side (DerivativeSide): Position side (long/short)

        Returns:
            Position | None: The removed position or None if not found
        """
        if not trading_pair.market_info.is_derivative:
            raise ValueError("Trading pair is not a derivative")

        asset = cast(
            DerivativeContract,
            AssetFactory.get_asset(self.platform, trading_pair.name, side=side),
        )
        return self.balance_tracker.remove_position(asset)

    # === Retrieving ===

    @abstractmethod
    async def update_all_balances(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_all_positions(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_balance(self, asset: Asset) -> None:
        raise NotImplementedError
