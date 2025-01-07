import asyncio
import logging
from abc import ABC, abstractmethod

from bidict import bidict

from financepype.rules.trading_rule import TradingRule


class TradingRulesTracker(ABC):
    _logger = None

    def __init__(self) -> None:
        self._trading_rules: dict[str, TradingRule] = {}
        self._trading_pair_symbol_map: bidict[str, str] | None = None
        self._mapping_initialization_lock = asyncio.Lock()

    @classmethod
    def logger(cls) -> logging.Logger:
        if cls._logger is None:
            cls._logger = logging.getLogger("rules")
        return cls._logger

    @property
    def trading_rules(self) -> dict[str, TradingRule]:
        return self._trading_rules

    @property
    def is_locked(self) -> bool:
        return self._mapping_initialization_lock.locked()

    @property
    def is_ready(self) -> bool:
        return self.trading_pair_symbol_map_ready()

    # === Mapping ===

    async def trading_pair_symbol_map(self) -> bidict[str, str]:
        if not self.is_ready:
            async with self._mapping_initialization_lock:
                if not self.is_ready:
                    await self.update_trading_rules()
        current_map = self._trading_pair_symbol_map or bidict()
        return current_map

    def trading_pair_symbol_map_ready(self) -> bool:
        """
        Checks if the mapping from exchange symbols to client trading pairs has been initialized

        :return: True if the mapping has been initialized, False otherwise
        """
        return (
            self._trading_pair_symbol_map is not None
            and len(self._trading_pair_symbol_map) > 0
        )

    async def all_trading_pairs(self) -> list[str]:
        """
        List of all trading pairs supported by the exchange

        :return: List of trading pair symbols in the bot format
        """
        mapping = await self.trading_pair_symbol_map()
        return list(mapping.values())

    async def all_exchange_symbols(self) -> list[str]:
        """
        List of all exchange symbols supported by the exchange

        :return: List of exchange symbols
        """
        mapping = await self.trading_pair_symbol_map()
        return list(mapping.keys())

    # === Conversions ===

    async def exchange_symbol_associated_to_pair(self, trading_pair: str) -> str:
        """
        Used to translate a trading pair from the client notation to the exchange notation

        :param trading_pair: trading pair in client notation

        :return: trading pair in exchange notation
        """
        symbol_map = await self.trading_pair_symbol_map()
        return symbol_map.inverse[trading_pair]

    async def trading_pair_associated_to_exchange_symbol(self, symbol: str) -> str:
        """
        Used to translate a trading pair from the exchange notation to the client notation

        :param symbol: trading pair in exchange notation

        :return: trading pair in client notation
        """
        symbol_map = await self.trading_pair_symbol_map()
        return symbol_map[symbol]

    # === Checks ===

    async def is_trading_pair_valid(self, trading_pair: str) -> bool:
        """
        Used to check if a trading pair is supported by the exchange

        :param trading_pair: trading pair in client notation

        :return: True if the trading pair is supported, False otherwise
        """
        symbol_map = await self.trading_pair_symbol_map()
        return trading_pair in symbol_map.inverse

    async def is_exchange_symbol_valid(self, symbol: str) -> bool:
        """
        Used to check if a trading pair is associated to the exchange symbol

        :param symbol: trading pair in exchange notation

        :return: True if the trading pair is associated to the exchange symbol, False otherwise
        """
        symbol_map = await self.trading_pair_symbol_map()
        return symbol in symbol_map

    def set_trading_pair_symbol_map(
        self, trading_pair_and_symbol_map: bidict[str, str] | None
    ) -> None:
        self._trading_pair_symbol_map = trading_pair_and_symbol_map

    def set_trading_rules(self, trading_rules: dict[str, TradingRule]) -> None:
        self._trading_rules = trading_rules

    def set_trading_rule(self, trading_pair: str, trading_rule: TradingRule) -> None:
        self._trading_rules[trading_pair] = trading_rule

    def remove_trading_rule(self, trading_pair: str) -> None:
        self._trading_rules.pop(trading_pair)

    # === Updating ===

    @abstractmethod
    async def update_trading_rules(self) -> None:
        raise NotImplementedError
