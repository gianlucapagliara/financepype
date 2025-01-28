from abc import abstractmethod
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

from financepype.constants import s_decimal_NaN
from financepype.markets.candle import Candle, CandleType
from financepype.markets.orderbook import OrderBook
from financepype.markets.orderbook.models import (
    ClientOrderBookQueryResult,
    ClientOrderBookRow,
)
from financepype.markets.orderbook.tracker import OrderBookTracker
from financepype.markets.trade import PublicTrade
from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import OrderType, PriceType
from financepype.operators.exchanges.exchange import Exchange, ExchangeConfiguration


class OrderBookExchange(Exchange):
    def __init__(self, configuration: ExchangeConfiguration):
        super().__init__(configuration)

        self._order_book_tracker: OrderBookTracker = self.init_order_book_tracker()

    @property
    def order_books(self) -> dict[TradingPair, OrderBook]:
        return self.order_book_tracker.order_books

    @property
    def order_book_tracker(self) -> OrderBookTracker:
        return self._order_book_tracker

    @property
    def supported_order_types(self) -> list[OrderType]:
        return [OrderType.LIMIT, OrderType.MARKET]

    @abstractmethod
    def init_order_book_tracker(self) -> OrderBookTracker:
        raise NotImplementedError

    # === Trading pairs ===

    def add_trading_pairs(self, trading_pairs: list[TradingPair]) -> None:
        """
        Adds new trading pairs to the connector. This will also add the trading pairs to the order book tracker.
        :param trading_pair: The trading pairs to add
        """
        self.order_book_tracker.add_trading_pairs(trading_pairs)

    def remove_trading_pairs(self, trading_pairs: list[TradingPair]) -> None:
        """
        Removes trading pairs from the connector. This will also remove the trading pairs from the order book tracker.
        :param trading_pairs: The trading pairs to remove
        """
        self.order_book_tracker.remove_trading_pairs(trading_pairs)

    # === Prices ===

    async def get_last_traded_prices(
        self, trading_pairs: list[TradingPair]
    ) -> dict[TradingPair, Decimal]:
        """
        Return a dictionary the trading_pair as key and the current price as value for each trading pair passed as
        parameter

        :param trading_pairs: list of trading pairs to get the prices for

        :return: Dictionary of associations between token pair and its latest price
        """
        raise NotImplementedError

    def get_mid_price(self, trading_pair: TradingPair) -> Decimal:
        return (
            self.get_price(trading_pair, True) + self.get_price(trading_pair, False)
        ) / 2

    def get_order_book(self, trading_pair: TradingPair) -> OrderBook:
        """
        Returns the current order book for a particular market

        :param trading_pair: the pair of tokens for which the order book should be retrieved
        """
        if trading_pair not in self.order_book_tracker.order_books:
            raise ValueError(f"No order book exists for '{trading_pair}'.")
        return self.order_book_tracker.order_books[trading_pair]

    def get_price(
        self, trading_pair: TradingPair, is_buy: bool, amount: Decimal = s_decimal_NaN
    ) -> Decimal:
        """
        :returns: Top bid/ask price for a specific trading pair
        """
        order_book = self.get_order_book(trading_pair)
        top_price = Decimal(str(order_book.get_price(is_buy)))
        return self.quantize_order_price(trading_pair, top_price)

    def get_vwap_for_volume(
        self, trading_pair: TradingPair, is_buy: bool, volume: Decimal
    ) -> ClientOrderBookQueryResult:
        order_book = self.get_order_book(trading_pair)
        result = order_book.get_vwap_for_volume(is_buy, float(volume))
        query_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.query_volume))
        )
        result_price = self.quantize_order_price(
            trading_pair, Decimal(str(result.result_price))
        )
        result_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.result_volume))
        )
        return ClientOrderBookQueryResult(
            s_decimal_NaN, query_volume, result_price, result_volume
        )

    def get_price_for_quote_volume(
        self, trading_pair: TradingPair, is_buy: bool, volume: Decimal
    ) -> ClientOrderBookQueryResult:
        order_book = self.get_order_book(trading_pair)
        result = order_book.get_price_for_quote_volume(is_buy, float(volume))
        query_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.query_volume))
        )
        result_price = self.quantize_order_price(
            trading_pair, Decimal(str(result.result_price))
        )
        result_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.result_volume))
        )
        return ClientOrderBookQueryResult(
            s_decimal_NaN, query_volume, result_price, result_volume
        )

    def get_price_for_volume(
        self, trading_pair: TradingPair, is_buy: bool, volume: Decimal
    ) -> ClientOrderBookQueryResult:
        order_book = self.get_order_book(trading_pair)
        result = order_book.get_price_for_volume(is_buy, float(volume))
        query_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.query_volume))
        )
        result_price = self.quantize_order_price(
            trading_pair, Decimal(str(result.result_price))
        )
        result_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.result_volume))
        )
        return ClientOrderBookQueryResult(
            s_decimal_NaN, query_volume, result_price, result_volume
        )

    def get_quote_volume_for_base_amount(
        self, trading_pair: TradingPair, is_buy: bool, base_amount: Decimal
    ) -> ClientOrderBookQueryResult:
        order_book = self.get_order_book(trading_pair)
        result = order_book.get_quote_volume_for_base_amount(is_buy, float(base_amount))
        query_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.query_volume))
        )
        result_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.result_volume))
        )
        return ClientOrderBookQueryResult(
            s_decimal_NaN, query_volume, s_decimal_NaN, result_volume
        )

    def get_volume_for_price(
        self, trading_pair: TradingPair, is_buy: bool, price: Decimal
    ) -> ClientOrderBookQueryResult:
        order_book = self.get_order_book(trading_pair)
        result = order_book.get_volume_for_price(is_buy, float(price))
        query_price = self.quantize_order_price(
            trading_pair, Decimal(str(result.query_price))
        )
        result_price = self.quantize_order_price(
            trading_pair, Decimal(str(result.result_price))
        )
        result_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.result_volume))
        )
        return ClientOrderBookQueryResult(
            query_price, s_decimal_NaN, result_price, result_volume
        )

    def get_quote_volume_for_price(
        self, trading_pair: TradingPair, is_buy: bool, price: Decimal
    ) -> ClientOrderBookQueryResult:
        order_book = self.get_order_book(trading_pair)
        result = order_book.get_volume_for_price(is_buy, float(price))
        query_price = self.quantize_order_price(
            trading_pair, Decimal(str(result.query_price))
        )
        result_price = self.quantize_order_price(
            trading_pair, Decimal(str(result.result_price))
        )
        result_volume = self.quantize_order_amount(
            trading_pair, Decimal(str(result.result_volume))
        )
        return ClientOrderBookQueryResult(
            query_price, s_decimal_NaN, result_price, result_volume
        )

    def order_book_bid_entries(
        self, trading_pair: TradingPair
    ) -> Iterator[ClientOrderBookRow]:
        order_book = self.get_order_book(trading_pair)
        for entry in order_book.bid_entries():
            yield ClientOrderBookRow(
                self.quantize_order_price(trading_pair, Decimal(str(entry.price))),
                self.quantize_order_amount(trading_pair, Decimal(str(entry.amount))),
                entry.update_id,
            )

    def order_book_ask_entries(
        self, trading_pair: TradingPair
    ) -> Iterator[ClientOrderBookRow]:
        order_book = self.get_order_book(trading_pair)
        for entry in order_book.ask_entries():
            yield ClientOrderBookRow(
                self.quantize_order_price(trading_pair, Decimal(str(entry.price))),
                self.quantize_order_amount(trading_pair, Decimal(str(entry.amount))),
                entry.update_id,
            )

    def get_bid_ask_spread_for_volume(
        self, trading_pair: TradingPair, volume: Decimal
    ) -> tuple[Decimal, Decimal]:
        ask_vwprice: Decimal = self.get_vwap_for_volume(
            trading_pair, True, volume
        ).result_price
        bid_vwprice: Decimal = self.get_vwap_for_volume(
            trading_pair, False, volume
        ).result_price
        if ask_vwprice.is_nan() or bid_vwprice.is_nan():
            return s_decimal_NaN, s_decimal_NaN
        return ask_vwprice - bid_vwprice, (
            (ask_vwprice / bid_vwprice) - Decimal("1")
        ) * Decimal("100")

    def get_price_by_type(
        self, trading_pair: TradingPair, price_type: PriceType
    ) -> Decimal:
        """
        Gets price by type (BestBid, BestAsk, MidPrice or LastTrade)
        :param trading_pair: The market trading pair
        :param price_type: The price type
        :returns The price
        """
        if price_type is PriceType.BestBid:
            return self.get_price(trading_pair, False)
        elif price_type is PriceType.BestAsk:
            return self.get_price(trading_pair, True)
        elif price_type is PriceType.MidPrice:
            return (
                self.get_price(trading_pair, True) + self.get_price(trading_pair, False)
            ) / Decimal("2")
        elif price_type is PriceType.LastTrade:
            return Decimal(str(self.get_order_book(trading_pair).last_trade_price))
        else:
            raise ValueError(f"Invalid price type: {price_type}")

    def get_quote_price(
        self, trading_pair: TradingPair, is_buy: bool, amount: Decimal
    ) -> Decimal:
        """
        For an exchange type connector, the quote price is volume weighted average price.
        """
        return Decimal(
            str(self.get_vwap_for_volume(trading_pair, is_buy, amount).result_price)
        )

    def get_order_price(
        self, trading_pair: TradingPair, is_buy: bool, amount: Decimal
    ) -> Decimal:
        """
        For an exchange type connector, the price required for order submission is the price of the order book for
        required volume.
        """
        return Decimal(
            str(self.get_price_for_volume(trading_pair, is_buy, amount).result_price)
        )

    # === Historical data ===

    @abstractmethod
    async def get_historical_trades(
        self,
        trading_pair: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[PublicTrade]:
        raise NotImplementedError

    @abstractmethod
    async def get_historical_candles(
        self,
        trading_pair: str,
        seconds_interval: int,
        exchange_interval: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        candle_type: CandleType = CandleType.PRICE,
    ) -> list[Candle]:
        raise NotImplementedError
