import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Iterable
from decimal import Decimal

import pandas as pd
from eventspype.pub.multipublisher import MultiPublisher
from eventspype.pub.publication import EventPublication

from financepype.markets.orderbook import OrderBook, OrderBookEvent
from financepype.markets.orderbook.models import (
    BaseOrderBookMessage,
    OrderBookMessageType,
    OrderBookTradeEvent,
    OrderBookTradeMessage,
    OrderBookUpdateEvent,
    OrderBookUpdateMessage,
)
from financepype.markets.trading_pair import TradingPair


class OrderBookTracker(MultiPublisher, ABC):
    def __init__(
        self, trading_pairs: Iterable[TradingPair], past_diffs_window_size: int = 32
    ):
        self._trading_pairs: set[TradingPair] = set(trading_pairs)
        self._order_books: dict[TradingPair, OrderBook] = {}
        self._event_publications: dict[TradingPair, EventPublication] = {}
        self._tracking_message_queues: dict[
            TradingPair, asyncio.Queue[BaseOrderBookMessage]
        ] = {}
        self._past_diffs_windows: dict[TradingPair, deque[OrderBookUpdateMessage]] = (
            defaultdict(lambda: deque(maxlen=past_diffs_window_size))
        )

        self._order_book_diff_stream: asyncio.Queue[OrderBookUpdateMessage] = (
            asyncio.Queue()
        )
        self._order_book_snapshot_stream: asyncio.Queue[BaseOrderBookMessage] = (
            asyncio.Queue()
        )
        self._order_book_trade_stream: asyncio.Queue[OrderBookTradeMessage] = (
            asyncio.Queue()
        )
        self._saved_message_queues: dict[TradingPair, deque[BaseOrderBookMessage]] = (
            defaultdict(lambda: deque(maxlen=1000))
        )

        self._tracking_tasks: dict[TradingPair, asyncio.Task[None]] = {}

        self._order_book_diff_router_task: asyncio.Task[None] | None = None
        self._order_book_snapshot_router_task: asyncio.Task[None] | None = None
        self._update_last_trade_prices_task: asyncio.Task[None] | None = None
        self._init_order_books_task: asyncio.Task[None] | None = None
        self._emit_trade_event_task: asyncio.Task[None] | None = None

        self._order_books_initialized: asyncio.Event = asyncio.Event()

    @abstractmethod
    @classmethod
    def logger(cls) -> logging.Logger:
        raise NotImplementedError

    @property
    def trading_pairs(self) -> set[TradingPair]:
        return set(self._trading_pairs)

    @property
    def order_books(self) -> dict[TradingPair, OrderBook]:
        return self._order_books

    @property
    def snapshot(self) -> dict[TradingPair, tuple[pd.DataFrame, pd.DataFrame]]:
        return {
            trading_pair: order_book.snapshot
            for trading_pair, order_book in self._order_books.items()
        }

    @property
    def ready(self) -> bool:
        return self._order_books_initialized.is_set()

    def start(self):
        self.stop(restart=True)

        if len(self.trading_pairs) > 0:
            self._order_book_diff_router_task = asyncio.ensure_future(
                self._order_book_diff_router()
            )
            self._order_book_snapshot_router_task = asyncio.ensure_future(
                self._order_book_snapshot_router()
            )
            self._update_last_trade_prices_task = asyncio.ensure_future(
                self._update_last_trade_prices_loop()
            )

        self._init_order_books_task = asyncio.ensure_future(self._init_order_books())
        self._emit_trade_event_task = asyncio.ensure_future(
            self._emit_trade_event_loop()
        )

    def stop(self, restart: bool = False):
        if self._init_order_books_task is not None:
            self._init_order_books_task.cancel()
            self._init_order_books_task = None
        if self._emit_trade_event_task is not None:
            self._emit_trade_event_task.cancel()
            self._emit_trade_event_task = None

        if self._order_book_diff_router_task is not None:
            self._order_book_diff_router_task.cancel()
            self._order_book_diff_router_task = None
        if self._order_book_snapshot_router_task is not None:
            self._order_book_snapshot_router_task.cancel()
            self._order_book_snapshot_router_task = None
        if self._update_last_trade_prices_task is not None:
            self._update_last_trade_prices_task.cancel()
            self._update_last_trade_prices_task = None

        if len(self._tracking_tasks) > 0:
            for _, task in self._tracking_tasks.items():
                task.cancel()
            self._tracking_tasks.clear()

        self._order_books_initialized.clear()

    def add_trading_pairs(self, trading_pairs: Iterable[TradingPair]) -> None:
        self._trading_pairs.update(trading_pairs)
        self._update_event_publications()

    def remove_trading_pairs(self, trading_pairs: Iterable[TradingPair]) -> None:
        self._trading_pairs.difference_update(trading_pairs)
        self._update_event_publications()

    @abstractmethod
    async def get_new_order_book(self, trading_pair: TradingPair) -> OrderBook:
        raise NotImplementedError

    @abstractmethod
    async def get_last_traded_prices(
        self, trading_pairs: list[TradingPair]
    ) -> dict[TradingPair, Decimal]:
        raise NotImplementedError

    def _update_event_publications(self) -> None:
        for trading_pair in self.trading_pairs:
            self._event_publications[trading_pair] = EventPublication(
                self.get_event_tag(trading_pair, OrderBookEvent.OrderBookUpdateEvent),
                OrderBookUpdateEvent,
            )

    async def _update_last_trade_prices_loop(self) -> None:
        """
        Updates last trade price for all order books through REST API, it is to initiate last_trade_price and as
        fall-back mechanism for when the web socket update channel fails.
        """
        await self._order_books_initialized.wait()
        while True:
            try:
                outdateds = [
                    t_pair
                    for t_pair, o_book in self._order_books.items()
                    if o_book.last_applied_trade < time.perf_counter() - (60.0 * 3)
                    and o_book.last_trade_price_rest_updated < time.perf_counter() - 5
                ]
                if outdateds:
                    last_prices = await self.get_last_traded_prices(
                        trading_pairs=outdateds
                    )
                    for trading_pair, last_price in last_prices.items():
                        self._order_books[trading_pair].last_trade_price = float(
                            last_price
                        )
                        self._order_books[
                            trading_pair
                        ].last_trade_price_rest_updated = time.perf_counter()
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if not isinstance(e, IndexError):
                    self.logger().warning(
                        "Unexpected error while fetching last trade price.",
                        exc_info=True,
                    )
                await asyncio.sleep(30)

    async def _init_order_books(self) -> None:
        """
        Initialize order books
        """
        retry = True
        while retry:
            try:
                for index, trading_pair in enumerate(self._trading_pairs):
                    self._order_books[trading_pair] = await self.get_new_order_book(
                        trading_pair
                    )
                    self._tracking_message_queues[trading_pair] = asyncio.Queue()
                    self._tracking_tasks[trading_pair] = asyncio.ensure_future(
                        self._track_single_book(trading_pair)
                    )
                    self.logger().info(
                        f"Initialized order book for {trading_pair}. "
                        f"{index + 1}/{len(self._trading_pairs)} completed."
                    )
                    await asyncio.sleep(1)
                self._order_books_initialized.set()
                retry = False
            except Exception:
                retry = True

    async def _order_book_diff_router(self) -> None:
        """
        Routes the real-time order book diff messages to the correct order book.
        """
        last_message_timestamp: float = time.time()
        messages_queued: int = 0
        messages_accepted: int = 0
        messages_rejected: int = 0

        while True:
            try:
                ob_message: OrderBookUpdateMessage = (
                    await self._order_book_diff_stream.get()
                )

                if ob_message.trading_pair not in self._tracking_message_queues:
                    messages_queued += 1
                    # Save diff messages received before snapshots are ready
                    self._saved_message_queues[ob_message.trading_pair].append(
                        ob_message
                    )
                    continue
                message_queue = self._tracking_message_queues[ob_message.trading_pair]
                # Check the order book's initial update ID. If it's larger, don't bother.
                order_book: OrderBook = self._order_books[ob_message.trading_pair]

                if order_book.snapshot_uid > ob_message.update_id:
                    messages_rejected += 1
                    continue
                await message_queue.put(ob_message)
                messages_accepted += 1

                # Log some statistics.
                now: float = time.time()
                if int(now / 60.0) > int(last_message_timestamp / 60.0):
                    self.logger().debug(
                        f"Diff messages processed: {messages_accepted}, "
                        f"rejected: {messages_rejected}, queued: {messages_queued}"
                    )
                    messages_accepted = 0
                    messages_rejected = 0
                    messages_queued = 0

                last_message_timestamp = now
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().warning(
                    "Unexpected error routing order book messages.", exc_info=True
                )
                await asyncio.sleep(5.0)

    async def _order_book_snapshot_router(self) -> None:
        """
        Route the real-time order book snapshot messages to the correct order book.
        """
        while True:
            try:
                ob_message = await self._order_book_snapshot_stream.get()
                if ob_message.trading_pair not in self._tracking_message_queues:
                    continue
                message_queue = self._tracking_message_queues[ob_message.trading_pair]
                await message_queue.put(ob_message)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().warning(
                    "Unknown error. Retrying after 5 seconds.", exc_info=True
                )
                await asyncio.sleep(5.0)

    async def _track_single_book(self, trading_pair: TradingPair) -> None:
        past_diffs_window = self._past_diffs_windows[trading_pair]

        message_queue = self._tracking_message_queues[trading_pair]
        order_book = self._order_books[trading_pair]

        await self._order_books_initialized.wait()
        while True:
            try:
                saved_messages = self._saved_message_queues[trading_pair]

                # Process saved messages first if there are any
                if len(saved_messages) > 0:
                    message = saved_messages.popleft()
                else:
                    message = await message_queue.get()

                if isinstance(message, OrderBookUpdateMessage):
                    if message.type is OrderBookMessageType.DIFF:
                        order_book.apply_diffs(
                            message.bids, message.asks, message.update_id
                        )
                        past_diffs_window.append(message)
                    elif message.type is OrderBookMessageType.SNAPSHOT:
                        past_diffs = list(past_diffs_window)
                        order_book.restore_from_snapshot_and_diffs(message, past_diffs)
                        self.logger().debug(
                            f"Processed order book snapshot for {trading_pair}."
                        )

                    self.trigger_event(
                        self._event_publications[trading_pair],
                        OrderBookUpdateEvent(
                            trading_pair=trading_pair,
                            timestamp=message.timestamp,
                        ),
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().warning(
                    f"Unexpected error tracking order book for {trading_pair}.",
                    exc_info=True,
                )
                await asyncio.sleep(5.0)

    async def _emit_trade_event_loop(self) -> None:
        """
        Process trade events from the trade stream and emit them to subscribers.
        """
        while True:
            try:
                message = await self._order_book_trade_stream.get()
                if message.trading_pair not in self._order_books:
                    continue
                order_book = self._order_books[message.trading_pair]
                order_book.apply_trade(
                    OrderBookTradeEvent(
                        trading_pair=message.trading_pair,
                        timestamp=message.timestamp,
                        price=message.price,
                        amount=message.amount,
                        type=message.trade_type,
                    )
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().warning(
                    "Unknown error. Retrying after 5 seconds.", exc_info=True
                )
                await asyncio.sleep(5.0)

    def get_event_tag(
        self, trading_pair: TradingPair, event_type: OrderBookEvent
    ) -> int:
        """
        Returns a unique tag for the given trading pair and event type.
        This tag is used to identify the event subscription.

        Args:
            trading_pair: The trading pair
            event_type: The type of event

        Returns:
            int: A unique tag for this event subscription
        """
        return hash((trading_pair, event_type))
