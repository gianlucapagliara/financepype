"""Trading rules tracking and validation system.

This module provides an abstract base class for tracking and managing trading rules
across different exchanges. It handles the mapping between exchange-specific symbols
and standardized trading pair formats, and maintains an up-to-date collection of
trading rules for each instrument.

The tracker provides thread-safe access to trading rules and symbol mappings,
with support for asynchronous updates and validations.

Example:
    >>> class BinanceRulesTracker(TradingRulesTracker):
    ...     async def update_trading_rules(self):
    ...         rules = await self.exchange.fetch_trading_rules()
    >>> tracker = BinanceRulesTracker()
    >>> await tracker.update_trading_rules()
    >>> print(await tracker.is_trading_pair_valid("BTC-USDT"))
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from bidict import bidict

from financepype.markets.trading_pair import TradingPair
from financepype.rules.trading_rule import TradingRule


class TradingRulesTracker(ABC):
    """Abstract base class for tracking and validating trading rules.

    This class provides the infrastructure for maintaining and accessing trading rules
    and symbol mappings for a specific exchange. It ensures thread-safe access to
    the data and provides methods for validating trading pairs and symbols.

    The class uses a bidirectional mapping between exchange-specific symbols and
    standardized trading pair formats, allowing for easy conversion in both directions.
    All operations are thread-safe and support asynchronous access.

    The actual implementation of rule updates should be provided by exchange-specific
    subclasses through the update_trading_rules method.

    Attributes:
        _trading_rules (dict[str, TradingRule]): Current trading rules by trading pair
        _trading_pair_symbol_map (bidict[str, str] | None): Bidirectional symbol mapping
        _mapping_initialization_lock (asyncio.Lock): Lock for thread-safe updates

    Example:
        >>> tracker = MyExchangeTracker()
        >>> await tracker.update_trading_rules()
        >>> rules = tracker.trading_rules
        >>> is_valid = await tracker.is_trading_pair_valid("BTC-USDT")
    """

    def __init__(self) -> None:
        """Initialize the trading rules tracker.

        Creates empty collections for trading rules and symbol mappings, and
        initializes the thread synchronization lock. The actual rules and
        mappings should be populated by calling update_trading_rules.
        """
        self._trading_rules: dict[TradingPair, TradingRule] = {}
        self._trading_pair_symbol_map: bidict[TradingPair, str] = bidict()
        self._mapping_initialization_lock = asyncio.Lock()

    @classmethod
    @abstractmethod
    def logger(cls) -> logging.Logger:
        """
        Returns the logger for the trading rules tracker.
        """
        raise NotImplementedError

    @property
    def trading_rules(self) -> dict[TradingPair, TradingRule]:
        """Get the current trading rules.

        This property provides read-only access to the current trading rules.
        The rules should only be modified through the set_trading_rules or
        set_trading_rule methods to ensure thread safety.

        Returns:
            dict[TradingPair, TradingRule]: Trading rules indexed by trading pair
        """
        return self._trading_rules

    @property
    def is_locked(self) -> bool:
        """Check if the tracker is currently updating its mappings.

        This property indicates whether there is an ongoing update operation
        that has acquired the initialization lock.

        Returns:
            bool: True if an update is in progress
        """
        return self._mapping_initialization_lock.locked()

    @property
    def is_ready(self) -> bool:
        """Check if the tracker has initialized its mappings.

        The tracker is considered ready when it has a non-empty symbol mapping.
        This indicates that at least one successful update has completed.

        Returns:
            bool: True if mappings are initialized and ready to use
        """
        return self.trading_pair_symbol_map_ready()

    async def trading_pair_symbol_map(self) -> bidict[TradingPair, str]:
        """Get the bidirectional mapping between exchange symbols and trading pairs.

        This method provides thread-safe access to the symbol mapping. If the
        mapping hasn't been initialized, it will trigger an update of the
        trading rules.

        Returns:
            bidict[TradingPair, str]: Bidirectional mapping between exchange symbols and trading pairs
        """
        if not self.is_ready:
            async with self._mapping_initialization_lock:
                if not self.is_ready:
                    await self.update_trading_rules()
        current_map = self._trading_pair_symbol_map
        return current_map

    def trading_pair_symbol_map_ready(self) -> bool:
        """Check if the symbol mapping has been initialized.

        The mapping is considered ready when it exists and contains at least
        one entry. This indicates that the initial update was successful.

        Returns:
            bool: True if the mapping exists and contains entries
        """
        return len(self._trading_pair_symbol_map) > 0

    async def all_trading_pairs(self) -> list[TradingPair]:
        """Get all available trading pairs.

        Returns a list of all trading pairs in the standardized format
        that are currently supported by the exchange.

        Returns:
            list[TradingPair]: List of all trading pairs in standardized format
        """
        mapping = await self.trading_pair_symbol_map()
        return list(mapping.keys())

    async def all_exchange_symbols(self) -> list[str]:
        """Get all available exchange symbols.

        Returns a list of all exchange-specific symbols that are
        currently supported by the exchange.

        Returns:
            list[str]: List of all exchange-specific symbols
        """
        mapping = await self.trading_pair_symbol_map()
        return list(mapping.values())

    async def exchange_symbol_associated_to_pair(
        self, trading_pair: TradingPair
    ) -> str:
        """Get the exchange-specific symbol for a trading pair.

        Converts a standardized trading pair format to the exchange's
        native symbol format.

        Args:
            trading_pair: Trading pair in standardized format

        Returns:
            str: Exchange-specific symbol

        Raises:
            KeyError: If the trading pair is not found in the mapping
        """
        mapping = await self.trading_pair_symbol_map()
        return mapping[trading_pair]

    async def trading_pair_associated_to_exchange_symbol(
        self, symbol: str
    ) -> TradingPair:
        """Get the standardized trading pair for an exchange symbol.

        Converts an exchange's native symbol format to the standardized
        trading pair format.

        Args:
            symbol: Exchange-specific symbol

        Returns:
            str: Trading pair in standardized format

        Raises:
            KeyError: If the symbol is not found in the mapping
        """
        mapping = await self.trading_pair_symbol_map()
        return mapping.inverse[symbol]

    async def is_trading_pair_valid(self, trading_pair: TradingPair) -> bool:
        """Check if a trading pair is valid and available for trading.

        A trading pair is considered valid if it exists in the symbol
        mapping and has associated trading rules.

        Args:
            trading_pair: Trading pair to validate

        Returns:
            bool: True if the trading pair is valid
        """
        mapping = await self.trading_pair_symbol_map()
        return trading_pair in mapping

    async def is_exchange_symbol_valid(self, symbol: str) -> bool:
        """Check if an exchange symbol is valid and available for trading.

        An exchange symbol is considered valid if it exists in the symbol
        mapping and has associated trading rules.

        Args:
            symbol: Exchange symbol to validate

        Returns:
            bool: True if the symbol is valid
        """
        mapping = await self.trading_pair_symbol_map()
        return symbol in mapping.inverse

    def set_trading_pair_symbol_map(
        self, trading_pair_and_symbol_map: bidict[TradingPair, str]
    ) -> None:
        """Update the symbol mapping.

        This method should be called by update_trading_rules to set
        the new mapping between exchange symbols and trading pairs.

        Args:
            trading_pair_and_symbol_map: New bidirectional mapping between
                exchange symbols and trading pairs
        """
        self._trading_pair_symbol_map = trading_pair_and_symbol_map

    def set_trading_rules(self, trading_rules: dict[TradingPair, TradingRule]) -> None:
        """Update all trading rules.

        This method replaces all existing trading rules with a new set.
        It should be called by update_trading_rules when new rules are
        fetched from the exchange.

        Args:
            trading_rules: New trading rules indexed by trading pair
        """
        self._trading_rules = trading_rules

    def set_trading_rule(
        self, trading_pair: TradingPair, trading_rule: TradingRule
    ) -> None:
        """Update the trading rule for a specific pair.

        This method updates or adds a trading rule for a single trading pair.
        It's useful for incremental updates when only some rules change.

        Args:
            trading_pair: Trading pair to update
            trading_rule: New trading rule for the pair
        """
        self._trading_rules[trading_pair] = trading_rule

    def remove_trading_rule(self, trading_pair: TradingPair) -> None:
        """Remove the trading rule for a specific pair.

        This method removes a trading rule when a trading pair is no longer
        available or supported.

        Args:
            trading_pair: Trading pair to remove

        Raises:
            KeyError: If the trading pair is not found
        """
        self._trading_rules.pop(trading_pair)

    @abstractmethod
    async def update_trading_rules(self) -> None:
        """Update trading rules from the exchange.

        This method should be implemented by exchange-specific subclasses to fetch
        and update trading rules from their respective exchanges. The implementation
        should:

        1. Fetch current trading rules from the exchange
        2. Convert exchange formats to TradingRule instances
        3. Update the symbol mapping using set_trading_pair_symbol_map
        4. Update the rules using set_trading_rules

        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError

    async def update_loop(self, interval_seconds: float):
        """
        Updates the trading rules by requesting the latest definitions from the exchange.
        Executes regularly every 30 minutes
        """
        while True:
            try:
                await asyncio.gather(self.update_trading_rules())
                await self._sleep(interval_seconds)
            except NotImplementedError:
                raise
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error(
                    "Unexpected error while fetching trading rules.",
                    exc_info=True,
                )
                await self._sleep(0.5)

    async def _sleep(self, seconds: float) -> None:
        """
        Sleeps for a given number of seconds.
        """
        await asyncio.sleep(seconds)
