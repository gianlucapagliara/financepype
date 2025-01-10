"""
This module implements an order book for financial markets, supporting both centralized and decentralized exchanges.
It provides functionality for maintaining bid and ask orders, processing order book updates, and calculating various
market metrics like VWAP, volume at price levels, and simulating trades.

The order book implementation uses efficient data structures (SortedSet) to maintain price levels and orders,
ensuring O(log n) performance for most operations. It supports both real-time updates through diffs and
full snapshots, making it suitable for both live trading and historical data analysis.

Key Features:
- Maintains bid and ask orders in sorted order
- Handles order book snapshots and incremental updates
- Provides various market metrics calculations
- Supports trade simulation
- Efficient memory usage and performance

Example:
    ```python
    # Create an order book instance
    order_book = OrderBook()

    # Apply a snapshot
    order_book.apply_snapshot(bids, asks, update_id=1000)

    # Apply incremental updates
    order_book.apply_diffs(new_bids, new_asks, update_id=1001)

    # Get best price
    best_bid = order_book.get_price(is_buy=False)
    best_ask = order_book.get_price(is_buy=True)

    # Simulate a trade
    execution_path = order_book.simulate_buy(amount=1.5)
    ```
"""

import bisect
import time
from collections.abc import Callable, Iterable, Iterator
from enum import Enum

import numpy as np
import pandas as pd
from sortedcontainers import SortedSet

from financepype.markets.orderbook.exceptions import OrderBookEmptyError
from financepype.markets.orderbook.models import (
    BaseOrderBookMessage,
    OrderBookEntry,
    OrderBookEvent,
    OrderBookQueryResult,
    OrderBookRow,
    OrderBookTradeEvent,
    OrderBookTradeMessage,
    OrderBookUpdateMessage,
)

# Public API exports
__all__ = [
    "OrderBook",
    "OrderBookEvent",
    "OrderBookEntry",
    "OrderBookQueryResult",
    "OrderBookRow",
    "OrderBookTradeEvent",
    "BaseOrderBookMessage",
    "OrderBookUpdateMessage",
    "OrderBookTradeMessage",
    "OrderBookEmptyError",
]


class OrderBook:
    """A limit order book implementation supporting both centralized and decentralized exchanges.

    This class maintains two sorted sets of orders (bids and asks) and provides methods for
    updating the order book state, querying prices and volumes, and simulating trades.
    It supports both full snapshots and incremental updates (diffs) for maintaining the
    order book state.

    The implementation uses SortedSet for efficient order management, providing O(log n)
    complexity for insertions, deletions, and lookups. For centralized exchanges, newer
    entries take precedence when there's a price overlap.

    Attributes:
        _snapshot_uid (int): ID of the last applied snapshot
        _last_diff_uid (int): ID of the last applied diff
        _best_bid (float): Current best bid price
        _best_ask (float): Current best ask price
        _last_trade_price (float): Price of the last executed trade
        _last_applied_trade (float): Timestamp of the last applied trade
        _last_trade_price_rest_updated (float): Timestamp of the last REST price update
        _bid_book (SortedSet): Collection of bid orders
        _ask_book (SortedSet): Collection of ask orders
    """

    def __init__(self) -> None:
        """Initialize an order book."""
        super().__init__()
        self._snapshot_uid: int = 0
        self._last_diff_uid: int = 0
        self._best_bid: float = float("NaN")
        self._best_ask: float = float("NaN")
        self._last_trade_price: float = float("NaN")
        self._last_applied_trade: float = -1000.0
        self._last_trade_price_rest_updated: float = -1000.0

        # Using SortedSet for O(log n) operations
        self._bid_book: set[OrderBookEntry] = SortedSet()  # Sorted in descending order
        self._ask_book: set[OrderBookEntry] = SortedSet()  # Sorted in ascending order

    def _truncate_overlap_entries(self) -> None:
        """Remove overlapping entries between bid and ask books.

        hen prices overlap, the newer entry (higher update_id) wins.
        """
        if not self._bid_book or not self._ask_book:
            return

        best_bid = max(self._bid_book, key=lambda x: x.price)
        best_ask = min(self._ask_book, key=lambda x: x.price)

        if best_bid.price >= best_ask.price:
            if best_bid.update_id > best_ask.update_id:
                self._ask_book.remove(best_ask)
            else:
                self._bid_book.remove(best_bid)

    def apply_diffs(
        self, bids: list[OrderBookRow], asks: list[OrderBookRow], update_id: int
    ) -> None:
        """Apply incremental updates (diffs) to the order book.

        This method processes lists of bid and ask updates, where each update contains
        a price level, amount, and update ID. Updates with amount=0 are treated as
        deletions. After applying the updates, it handles any price overlaps according
        to venue rules and updates the best bid/ask prices.

        Args:
            bids: List of bid updates (price, amount, update_id)
            asks: List of ask updates (price, amount, update_id)
            update_id: Unique identifier for this update batch
        """
        # Process bids
        for bid in bids:
            entry = OrderBookEntry(bid.price, bid.amount, bid.update_id)
            # Remove existing entry at this price level
            existing = [b for b in self._bid_book if b.price == entry.price]
            if existing:
                self._bid_book.remove(existing[0])
            # Add new entry if amount > 0
            if entry.amount > 0:
                self._bid_book.add(entry)

        # Process asks
        for ask in asks:
            entry = OrderBookEntry(ask.price, ask.amount, ask.update_id)
            # Remove existing entry at this price level
            existing = [a for a in self._ask_book if a.price == entry.price]
            if existing:
                self._ask_book.remove(existing[0])
            # Add new entry if amount > 0
            if entry.amount > 0:
                self._ask_book.add(entry)

        # Handle overlapping entries
        self._truncate_overlap_entries()

        # Update best prices
        if self._bid_book:
            self._best_bid = max(self._bid_book, key=lambda x: x.price).price
        if self._ask_book:
            self._best_ask = min(self._ask_book, key=lambda x: x.price).price

        # Update last diff ID
        self._last_diff_uid = update_id

    def apply_snapshot(
        self,
        bids: list[OrderBookRow] | None,
        asks: list[OrderBookRow] | None,
        update_id: int,
    ) -> None:
        """Apply a full order book snapshot.

        This method replaces the current order book state with a new snapshot.
        It optionally updates either or both sides of the book (bids/asks).
        After applying the snapshot, it handles any price overlaps and updates
        the best bid/ask prices.

        Args:
            bids: List of all bid orders, or None to keep current bids
            asks: List of all ask orders, or None to keep current asks
            update_id: Unique identifier for this snapshot
        """

        # Clear and update bid book
        if bids is not None:
            self._bid_book.clear()
            best_bid_price = float("NaN")
            for bid in bids:
                entry = OrderBookEntry(bid.price, bid.amount, bid.update_id)
                self._bid_book.add(entry)
                if not (entry.price <= best_bid_price):
                    best_bid_price = entry.price

        # Clear and update ask book
        if asks is not None:
            self._ask_book.clear()
            best_ask_price = float("NaN")
            for ask in asks:
                entry = OrderBookEntry(ask.price, ask.amount, ask.update_id)
                self._ask_book.add(entry)
                if not (entry.price >= best_ask_price):
                    best_ask_price = entry.price

        # Update best prices
        if best_bid_price != float("NaN"):
            self._best_bid = best_bid_price
        if best_ask_price != float("NaN"):
            self._best_ask = best_ask_price

        # Update snapshot ID
        self._snapshot_uid = update_id

    def apply_trade(self, trade: OrderBookTradeEvent) -> None:
        """Apply a trade event to the order book.

        Updates the last trade price and timestamp. This method is typically
        called when a trade occurs in the market, allowing the order book
        to track the most recent trade information.

        Args:
            trade: Trade event containing price, amount, and type
        """
        self._last_trade_price = trade.price
        self._last_applied_trade = time.perf_counter()

    def apply_pandas_diffs(self, bids_df: pd.DataFrame, asks_df: pd.DataFrame) -> None:
        """Apply order book updates from pandas DataFrames.

        A convenience method that converts DataFrame updates to numpy arrays
        and applies them as diffs. The DataFrames should have columns for
        price, amount, and update_id.

        Args:
            bids_df: DataFrame containing bid updates
            asks_df: DataFrame containing ask updates
        """
        self.apply_numpy_diffs(bids_df.values, asks_df.values)

    def apply_numpy_diffs(
        self,
        bids_array: np.ndarray[tuple[int, ...], np.dtype[np.float64]],
        asks_array: np.ndarray[tuple[int, ...], np.dtype[np.float64]],
    ) -> None:
        """Apply order book updates from numpy arrays.

        A convenience method that converts numpy array updates to OrderBookRow
        objects and applies them as diffs.

        Args:
            bids_array: Array containing bid updates (price, amount, update_id)
            asks_array: Array containing ask updates (price, amount, update_id)
        """
        bids = [
            OrderBookRow(float(price), float(amount), int(update_id))
            for price, amount, update_id in bids_array
        ]
        asks = [
            OrderBookRow(float(price), float(amount), int(update_id))
            for price, amount, update_id in asks_array
        ]
        self.apply_diffs(
            bids, asks, int(max(bids_array[:, 2].max(), asks_array[:, 2].max()))
        )

    def apply_numpy_snapshot(
        self,
        bids_array: np.ndarray[tuple[int, ...], np.dtype[np.float64]],
        asks_array: np.ndarray[tuple[int, ...], np.dtype[np.float64]],
    ) -> None:
        """Apply order book snapshot from numpy arrays.

        A convenience method that converts numpy array snapshots to OrderBookRow
        objects and applies them as a snapshot.

        Args:
            bids_array: Array containing all bid orders (price, amount, update_id)
            asks_array: Array containing all ask orders (price, amount, update_id)
        """
        bids = [
            OrderBookRow(float(price), float(amount), int(update_id))
            for price, amount, update_id in bids_array
        ]
        asks = [
            OrderBookRow(float(price), float(amount), int(update_id))
            for price, amount, update_id in asks_array
        ]
        self.apply_snapshot(
            bids, asks, int(max(bids_array[:, 2].max(), asks_array[:, 2].max()))
        )

    def bid_entries(self) -> Iterator[OrderBookRow]:
        """Get bid entries in descending order (best/highest bids first).

        Returns:
            Iterator yielding bid entries as OrderBookRow objects
        """
        for entry in sorted(self._bid_book, key=lambda x: (-x.price, x.update_id)):
            yield OrderBookRow(entry.price, entry.amount, entry.update_id)

    def ask_entries(self) -> Iterator[OrderBookRow]:
        """Get ask entries in ascending order (best/lowest asks first).

        Returns:
            Iterator yielding ask entries as OrderBookRow objects
        """
        for entry in sorted(self._ask_book, key=lambda x: (x.price, x.update_id)):
            yield OrderBookRow(entry.price, entry.amount, entry.update_id)

    def simulate_buy(self, amount: float) -> list[OrderBookRow]:
        """Simulate a market buy order of the specified amount.

        Walks the ask side of the order book to determine which orders would
        be filled by a market buy order of the given size. This is useful for
        estimating the cost and price impact of a potential trade.

        Args:
            amount: The amount to buy

        Returns:
            List of OrderBookRow objects that would be filled
        """
        amount_left = amount
        retval = []
        for ask_entry in self.ask_entries():
            if ask_entry.amount < amount_left:
                retval.append(ask_entry)
                amount_left -= ask_entry.amount
            else:
                retval.append(
                    OrderBookRow(ask_entry.price, amount_left, ask_entry.update_id)
                )
                amount_left = 0.0
                break
        return retval

    def simulate_sell(self, amount: float) -> list[OrderBookRow]:
        """Simulate a market sell order of the specified amount.

        Walks the bid side of the order book to determine which orders would
        be filled by a market sell order of the given size. This is useful for
        estimating the proceeds and price impact of a potential trade.

        Args:
            amount: The amount to sell

        Returns:
            List of OrderBookRow objects that would be filled
        """
        amount_left = amount
        retval = []
        for bid_entry in self.bid_entries():
            if bid_entry.amount < amount_left:
                retval.append(bid_entry)
                amount_left -= bid_entry.amount
            else:
                retval.append(
                    OrderBookRow(bid_entry.price, amount_left, bid_entry.update_id)
                )
                amount_left = 0.0
                break
        return retval

    def get_price(self, is_buy: bool) -> float:
        """Get the best available price for a buy or sell order.

        Args:
            is_buy: True for best ask (buying), False for best bid (selling)

        Returns:
            The best available price

        Raises:
            OrderBookEmptyError: If the order book is empty
        """
        book = self._ask_book if is_buy else self._bid_book
        if not book:
            raise OrderBookEmptyError(
                "Order book is empty - no price quote is possible."
            )
        return self._best_ask if is_buy else self._best_bid

    def get_price_for_volume(self, is_buy: bool, volume: float) -> OrderBookQueryResult:
        """Get the worst price needed to fill the specified volume.

        Walks the order book to find the price at which the entire volume
        could be filled. This represents the worst price you would get
        when executing a market order of the given size.

        Args:
            is_buy: True for buying, False for selling
            volume: The volume to fill

        Returns:
            OrderBookQueryResult with the price and available volume
        """
        cumulative_volume = 0
        result_price = float("NaN")

        if is_buy:
            for order_book_row in self.ask_entries():
                cumulative_volume += order_book_row.amount
                if cumulative_volume >= volume:
                    result_price = order_book_row.price
                    break
        else:
            for order_book_row in self.bid_entries():
                cumulative_volume += order_book_row.amount
                if cumulative_volume >= volume:
                    result_price = order_book_row.price
                    break

        return OrderBookQueryResult(
            float("NaN"), volume, result_price, min(cumulative_volume, volume)
        )

    def get_vwap_for_volume(self, is_buy: bool, volume: float) -> OrderBookQueryResult:
        """Calculate the Volume-Weighted Average Price (VWAP) for the specified volume.

        Computes the average price you would get when executing a market order
        of the given size, weighted by the volume at each price level.

        Args:
            is_buy: True for buying, False for selling
            volume: The volume to calculate VWAP for

        Returns:
            OrderBookQueryResult with the VWAP and available volume
        """
        total_cost = 0
        total_volume = 0
        result_vwap = float("NaN")

        if volume == 0:
            result_vwap = self.get_price(is_buy)
        else:
            if is_buy:
                for order_book_row in self.ask_entries():
                    total_cost += order_book_row.amount * order_book_row.price
                    total_volume += order_book_row.amount
                    if total_volume >= volume:
                        total_cost -= order_book_row.amount * order_book_row.price
                        total_volume -= order_book_row.amount
                        incremental_amount = volume - total_volume
                        total_cost += incremental_amount * order_book_row.price
                        total_volume += incremental_amount
                        result_vwap = total_cost / total_volume
                        break
            else:
                for order_book_row in self.bid_entries():
                    total_cost += order_book_row.amount * order_book_row.price
                    total_volume += order_book_row.amount
                    if total_volume >= volume:
                        total_cost -= order_book_row.amount * order_book_row.price
                        total_volume -= order_book_row.amount
                        incremental_amount = volume - total_volume
                        total_cost += incremental_amount * order_book_row.price
                        total_volume += incremental_amount
                        result_vwap = total_cost / total_volume
                        break

        return OrderBookQueryResult(
            float("NaN"), volume, result_vwap, min(total_volume, volume)
        )

    def get_price_for_quote_volume(
        self, is_buy: bool, quote_volume: float
    ) -> OrderBookQueryResult:
        """Get the price needed to fill the specified quote currency volume.

        Similar to get_price_for_volume, but works with quote currency amounts
        instead of base currency amounts. Useful when you want to spend/receive
        a specific amount of quote currency.

        Args:
            is_buy: True for buying, False for selling
            quote_volume: The amount of quote currency to fill

        Returns:
            OrderBookQueryResult with the price and available volume
        """
        cumulative_volume = 0
        result_price = float("NaN")

        if is_buy:
            for order_book_row in self.ask_entries():
                cumulative_volume += order_book_row.amount * order_book_row.price
                if cumulative_volume >= quote_volume:
                    result_price = order_book_row.price
                    break
        else:
            for order_book_row in self.bid_entries():
                cumulative_volume += order_book_row.amount * order_book_row.price
                if cumulative_volume >= quote_volume:
                    result_price = order_book_row.price
                    break

        return OrderBookQueryResult(
            float("NaN"),
            quote_volume,
            result_price,
            min(cumulative_volume, quote_volume),
        )

    def get_quote_volume_for_base_amount(
        self, is_buy: bool, base_amount: float
    ) -> OrderBookQueryResult:
        """Calculate the quote currency volume needed for a base currency amount.

        Useful for determining how much quote currency you need to spend (when buying)
        or will receive (when selling) for a given amount of base currency.

        Args:
            is_buy: True for buying, False for selling
            base_amount: The amount of base currency

        Returns:
            OrderBookQueryResult with the required quote currency volume
        """
        cumulative_volume = 0
        cumulative_base_amount = 0
        row_amount = 0

        if is_buy:
            for order_book_row in self.ask_entries():
                row_amount = order_book_row.amount
                if row_amount + cumulative_base_amount >= base_amount:
                    row_amount = base_amount - cumulative_base_amount
                cumulative_base_amount += row_amount
                cumulative_volume += row_amount * order_book_row.price
                if cumulative_base_amount >= base_amount:
                    break
        else:
            for order_book_row in self.bid_entries():
                row_amount = order_book_row.amount
                if row_amount + cumulative_base_amount >= base_amount:
                    row_amount = base_amount - cumulative_base_amount
                cumulative_base_amount += row_amount
                cumulative_volume += row_amount * order_book_row.price
                if cumulative_base_amount >= base_amount:
                    break

        return OrderBookQueryResult(
            float("NaN"), base_amount, float("NaN"), cumulative_volume
        )

    def get_volume_for_price(self, is_buy: bool, price: float) -> OrderBookQueryResult:
        """Get the total volume available at or better than the specified price.

        Calculates how much volume you can trade at a price equal to or better
        than the specified price.

        Args:
            is_buy: True for buying, False for selling
            price: The price threshold

        Returns:
            OrderBookQueryResult with the available volume
        """
        cumulative_volume = 0
        result_price = float("NaN")

        if is_buy:
            for order_book_row in self.ask_entries():
                if order_book_row.price > price:
                    break
                cumulative_volume += order_book_row.amount
                result_price = order_book_row.price
        else:
            for order_book_row in self.bid_entries():
                if order_book_row.price < price:
                    break
                cumulative_volume += order_book_row.amount
                result_price = order_book_row.price

        return OrderBookQueryResult(
            price, float("NaN"), result_price, cumulative_volume
        )

    def get_quote_volume_for_price(
        self, is_buy: bool, price: float
    ) -> OrderBookQueryResult:
        """Get the total quote currency volume available at or better than the specified price.

        Similar to get_volume_for_price, but returns the volume in quote currency
        instead of base currency.

        Args:
            is_buy: True for buying, False for selling
            price: The price threshold

        Returns:
            OrderBookQueryResult with the available quote currency volume
        """
        cumulative_volume = 0
        result_price = float("NaN")

        if is_buy:
            for order_book_row in self.ask_entries():
                if order_book_row.price > price:
                    break
                cumulative_volume += order_book_row.amount * order_book_row.price
                result_price = order_book_row.price
        else:
            for order_book_row in self.bid_entries():
                if order_book_row.price < price:
                    break
                cumulative_volume += order_book_row.amount * order_book_row.price
                result_price = order_book_row.price

        return OrderBookQueryResult(
            price, float("NaN"), result_price, cumulative_volume
        )

    def restore_from_snapshot_and_diffs(
        self, snapshot: OrderBookUpdateMessage, diffs: list[OrderBookUpdateMessage]
    ) -> None:
        """Restore the order book state from a snapshot and subsequent diffs.

        This method is useful for reconstructing the order book state from historical
        data or when recovering from a disconnect. It applies a snapshot and then
        replays all diffs that occurred after the snapshot.

        Args:
            snapshot: The base order book state
            diffs: List of subsequent updates to apply
        """
        replay_position = bisect.bisect_right(diffs, snapshot)
        replay_diffs = diffs[replay_position:]
        self.apply_snapshot(snapshot.bids, snapshot.asks, snapshot.update_id)
        for diff in replay_diffs:
            self.apply_diffs(diff.bids, diff.asks, diff.update_id)

    # Properties
    @property
    def last_trade_price(self) -> float:
        """The price of the last executed trade."""
        return self._last_trade_price

    @last_trade_price.setter
    def last_trade_price(self, value: float) -> None:
        """Set the price of the last executed trade."""
        self._last_trade_price = value

    @property
    def last_applied_trade(self) -> float:
        """Timestamp of the last applied trade."""
        return self._last_applied_trade

    @property
    def last_trade_price_rest_updated(self) -> float:
        """Timestamp of the last REST API price update."""
        return self._last_trade_price_rest_updated

    @last_trade_price_rest_updated.setter
    def last_trade_price_rest_updated(self, value: float) -> None:
        """Set the timestamp of the last REST API price update."""
        self._last_trade_price_rest_updated = value

    @property
    def snapshot_uid(self) -> int:
        """ID of the last applied snapshot."""
        return self._snapshot_uid

    @property
    def last_diff_uid(self) -> int:
        """ID of the last applied diff update."""
        return self._last_diff_uid

    @property
    def snapshot(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Get the current order book state as pandas DataFrames.

        Returns:
            tuple[pd.DataFrame, pd.DataFrame]: (bids_df, asks_df) containing
            price, amount, and update_id columns
        """
        bids_data = [
            (entry.price, entry.amount, entry.update_id) for entry in self._bid_book
        ]
        asks_data = [
            (entry.price, entry.amount, entry.update_id) for entry in self._ask_book
        ]

        columns = ["price", "amount", "update_id"]
        bids_df = (
            pd.DataFrame(bids_data, columns=columns)
            if bids_data
            else pd.DataFrame(columns=columns)
        )
        asks_df = (
            pd.DataFrame(asks_data, columns=columns)
            if asks_data
            else pd.DataFrame(columns=columns)
        )

        return bids_df, asks_df
