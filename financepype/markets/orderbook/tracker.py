import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from decimal import Decimal

import pandas as pd
from eventspype.pub.multipublisher import MultiPublisher
from eventspype.pub.publication import EventPublication

from financepype.markets.orderbook import OrderBook, OrderBookEvent
from financepype.markets.orderbook.models import (
    OrderBookUpdateEvent,
)
from financepype.markets.trading_pair import TradingPair


class OrderBookTracker(MultiPublisher, ABC):
    """
    Abstract base class defining the interface for order book trackers.

    This class defines the contract that all order book tracker implementations
    must follow, without prescribing any particular execution model (async, sync,
    tick-based, etc.). Concrete implementations should handle task management,
    message routing, and lifecycle according to their execution model.
    """

    _logger: logging.Logger | None = None

    orderbook_update_publication = EventPublication(
        "OrderBookUpdateEvent", OrderBookUpdateEvent
    )

    @classmethod
    def logger(cls) -> logging.Logger:
        if cls._logger is None:
            cls._logger = logging.getLogger(cls.__name__)
        return cls._logger

    # === Properties ===

    @property
    @abstractmethod
    def trading_pairs(self) -> set[TradingPair]:
        """The set of trading pairs being tracked."""
        ...

    @property
    @abstractmethod
    def order_books(self) -> dict[TradingPair, OrderBook]:
        """The current order books for all tracked trading pairs."""
        ...

    @property
    @abstractmethod
    def snapshot(self) -> dict[TradingPair, tuple[pd.DataFrame, pd.DataFrame]]:
        """Snapshot of all order books as (bids_df, asks_df) tuples."""
        ...

    @property
    @abstractmethod
    def ready(self) -> bool:
        """Whether the tracker is initialized and ready to serve data."""
        ...

    # === Lifecycle ===

    @abstractmethod
    def start(self) -> None:
        """Start the tracker. Implementation defines the execution model."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the tracker and clean up resources."""
        ...

    # === Trading pair management ===

    @abstractmethod
    def add_trading_pairs(self, trading_pairs: Iterable[TradingPair]) -> None:
        """Add trading pairs to track."""
        ...

    @abstractmethod
    def remove_trading_pairs(self, trading_pairs: Iterable[TradingPair]) -> None:
        """Remove trading pairs from tracking."""
        ...

    # === Data retrieval (abstract — may be sync or async in subclasses) ===

    @abstractmethod
    def get_new_order_book(self, trading_pair: TradingPair) -> OrderBook:
        """Create or fetch an initial order book for a trading pair."""
        ...

    @abstractmethod
    def get_last_traded_prices(
        self, trading_pairs: list[TradingPair]
    ) -> dict[TradingPair, Decimal]:
        """Get the last traded prices for the given trading pairs."""
        ...

    # === Event helpers ===

    @staticmethod
    def get_event_tag(trading_pair: TradingPair, event_type: OrderBookEvent) -> int:
        """
        Returns a unique tag for the given trading pair and event type.
        This tag is used to identify the event subscription.
        """
        return hash((trading_pair, event_type))
