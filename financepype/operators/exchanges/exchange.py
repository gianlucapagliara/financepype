import asyncio
from abc import abstractmethod
from decimal import Decimal
from hashlib import md5

from bidict import bidict

from financepype.constants import s_decimal_0, s_decimal_min, s_decimal_NaN
from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import (
    OrderModifier,
    OrderState,
    OrderType,
    OrderUpdate,
    TradeType,
)
from financepype.operations.orders.order import OrderOperation
from financepype.operators.operator import Operator, OperatorConfiguration
from financepype.owners.owner import Owner
from financepype.platforms.platform import Platform
from financepype.rules.trading_rule import TradingRule
from financepype.rules.trading_rules_tracker import TradingRulesTracker
from financepype.simulations.balances.engines.models import OrderDetails


class ExchangeConfiguration(OperatorConfiguration):
    platform: Platform


class Exchange(Operator):
    """Base class for cryptocurrency exchange operators.

    This class provides a standardized interface for interacting with different
    cryptocurrency exchanges. It handles common exchange operations such as:
    - Trading pair management
    - Order creation and cancellation
    - Price and size quantization
    - Trading rules enforcement

    The class implements core exchange functionality while leaving exchange-specific
    implementations to subclasses through abstract methods.

    Attributes:
        _trading_rules_tracker (TradingRulesTracker | None): Tracks trading rules
        _trading_pairs (list[str]): List of supported trading pairs

    Example:
        >>> exchange = BinanceExchange(Platform("binance"))
        >>> price = exchange.get_price("BTC-USDT", is_buy=True)
        >>> order_id = exchange.place_order(account, order_details)
    """

    def __init__(self, configuration: ExchangeConfiguration):
        """Initialize a new exchange operator.

        Args:
            configuration (ExchangeConfiguration): The configuration for the exchange
        """
        super().__init__(configuration)

        self._trading_pairs: list[str] = []
        self._trading_rules_tracker: TradingRulesTracker | None = None
        # self._order_tracker: OrderTracker = ...

        self.init_trading_rules_tracker()

    # === Properties ===

    @property
    def trading_rules(self) -> dict[TradingPair, TradingRule]:
        """Get the current trading rules.

        Returns:
            dict[str, TradingRule]: Map of trading pairs to their rules
        """
        if self.trading_rules_tracker is None:
            return {}
        return self.trading_rules_tracker.trading_rules

    @property
    def trading_rules_tracker(self) -> TradingRulesTracker | None:
        """Get the trading rules tracker.

        Returns:
            TradingRulesTracker | None: The rules tracker instance
        """
        return self._trading_rules_tracker

    @property
    def trading_pairs(self) -> list[str]:
        """Get supported trading pairs.

        Returns:
            list[str]: List of supported trading pair symbols
        """
        return self._trading_pairs

    @property
    @abstractmethod
    def supported_order_types(self) -> list[OrderType]:
        """Get supported order types.

        Returns:
            list[OrderType]: List of supported order types

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_order_modifiers(self) -> list[OrderModifier]:
        """Get supported order modifiers.

        Returns:
            list[OrderModifier]: List of supported order modifiers

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_create_request_in_exchange_synchronous(self) -> bool:
        """Check if order creation is synchronous.

        Returns:
            bool: True if order creation is synchronous

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        """Check if order cancellation is synchronous.

        Returns:
            bool: True if order cancellation is synchronous

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    # === Trading Pairs/Rules ===

    @abstractmethod
    def init_trading_rules_tracker(self) -> None:
        raise NotImplementedError

    def get_valid_trading_pairs(
        self, trading_pairs: str | list[str] | None = None
    ) -> list[str]:
        valid_trading_pairs = self.trading_pairs

        if trading_pairs is None:
            trading_pairs = []
        if isinstance(trading_pairs, str):
            trading_pairs = [trading_pairs]
        if len(trading_pairs) > 0:
            valid_trading_pairs = [
                trading_pair
                for trading_pair in trading_pairs
                if trading_pair in valid_trading_pairs
            ]
        return valid_trading_pairs

    async def trading_pair_symbol_map(self) -> bidict[TradingPair, str]:
        if self.trading_rules_tracker is None:
            return bidict()
        return await self.trading_rules_tracker.trading_pair_symbol_map()

    def trading_pair_symbol_map_ready(self) -> bool:
        if self.trading_rules_tracker is None:
            return False
        return self.trading_rules_tracker.is_ready

    async def all_trading_pairs(self) -> list[TradingPair]:
        if self.trading_rules_tracker is None:
            return []
        return await self.trading_rules_tracker.all_trading_pairs()

    async def all_exchange_symbols(self) -> list[str]:
        if self.trading_rules_tracker is None:
            return []
        return await self.trading_rules_tracker.all_exchange_symbols()

    async def exchange_symbol_associated_to_pair(
        self, trading_pair: TradingPair
    ) -> str:
        if self.trading_rules_tracker is None:
            return trading_pair.name
        return await self.trading_rules_tracker.exchange_symbol_associated_to_pair(
            trading_pair
        )

    async def is_trading_pair_valid(self, trading_pair: TradingPair) -> bool:
        if self.trading_rules_tracker is None:
            return False
        return await self.trading_rules_tracker.is_trading_pair_valid(trading_pair)

    async def trading_pair_associated_to_exchange_symbol(
        self, symbol: str
    ) -> TradingPair:
        if self.trading_rules_tracker is None:
            raise ValueError("Trading rules tracker is not initialized")
        return (
            await self.trading_rules_tracker.trading_pair_associated_to_exchange_symbol(
                symbol
            )
        )

    async def is_exchange_symbol_valid(self, symbol: str) -> bool:
        if self.trading_rules_tracker is None:
            return False
        return await self.trading_rules_tracker.is_exchange_symbol_valid(symbol)

    # === Price/Size Functions ===

    @abstractmethod
    def get_price(
        self, trading_pair: TradingPair, is_buy: bool, amount: Decimal = s_decimal_NaN
    ) -> Decimal:
        raise NotImplementedError

    @abstractmethod
    def get_quote_price(
        self, trading_pair: TradingPair, is_buy: bool, amount: Decimal
    ) -> Decimal:
        raise NotImplementedError

    @abstractmethod
    def get_order_price(
        self, trading_pair: TradingPair, is_buy: bool, amount: Decimal
    ) -> Decimal:
        raise NotImplementedError

    def get_order_price_quantum(
        self, trading_pair: TradingPair, price: Decimal = s_decimal_0
    ) -> Decimal:
        trading_rule = self.trading_rules[trading_pair]
        min_price_significance = trading_rule.min_price_significance
        min_price_increment = trading_rule.min_price_increment or s_decimal_min
        if min_price_significance:
            if price == s_decimal_0:
                price = self.get_price(trading_pair, True)
            integer_number = int(price)
            if integer_number == s_decimal_0:
                str_price_decimals = f"{price:f}".split(".")[1]
                int_price_decimals = int(str_price_decimals)
                leading_zeros = len(str_price_decimals) - len(str(int_price_decimals))
                price_quantum_significance = Decimal(
                    str(10 ** (-leading_zeros - min_price_significance))
                )
            else:
                integer_digits = len(str(integer_number))
                price_quantum_significance = Decimal(
                    str(10 ** (integer_digits - min_price_significance))
                )
        else:
            price_quantum_significance = s_decimal_min
        return max(min_price_increment, price_quantum_significance)

    def get_order_size_quantum(
        self, trading_pair: TradingPair, order_size: Decimal = s_decimal_0
    ) -> Decimal:
        trading_rule = self.trading_rules[trading_pair]
        return Decimal(trading_rule.min_base_amount_increment)

    def quantize_order_amount(
        self, trading_pair: TradingPair, amount: Decimal, price: Decimal = s_decimal_0
    ) -> Decimal:
        trading_rule = self.trading_rules[trading_pair]
        quantized_amount = self._quantize_order_amount(trading_pair, amount)

        # Check against min_order_size and min_notional_size. If not passing either check, return 0.
        if quantized_amount < trading_rule.min_order_size:
            return s_decimal_0

        if price == s_decimal_0 or price.is_nan():
            price = self.get_price(trading_pair, False)
        notional_size = price * quantized_amount

        # Add 1% as a safety factor in case the prices changed while making the order.
        if notional_size < trading_rule.min_notional_size * Decimal("1.01"):
            return s_decimal_0

        return quantized_amount

    def _quantize_order_amount(
        self, trading_pair: TradingPair, amount: Decimal
    ) -> Decimal:
        order_size_quantum = self.get_order_size_quantum(trading_pair, amount)
        return (amount // order_size_quantum) * order_size_quantum

    def _quantize_order_price(
        self, trading_pair: TradingPair, price: Decimal
    ) -> Decimal:
        if price.is_nan():
            return price
        price_quantum = self.get_order_price_quantum(trading_pair, price)
        return (price // price_quantum) * price_quantum

    def quantize_order_price(
        self,
        trading_pair: TradingPair,
        price: Decimal,
        trade_type: TradeType | None = None,
        is_aggressive: bool = False,
    ) -> Decimal:
        quantize_price = self._quantize_order_price(trading_pair, price)
        if trade_type is None or (quantize_price - price) == s_decimal_0:
            return quantize_price

        if trade_type is TradeType.BUY:
            if is_aggressive:
                return quantize_price + self.get_order_price_quantum(
                    trading_pair, price
                )
            return quantize_price
        else:
            if is_aggressive:
                return quantize_price
            return quantize_price + self.get_order_price_quantum(trading_pair, price)

    # === Orders Functions ===

    def get_new_client_operation_id(
        self,
        order_details: OrderDetails,
        client_operation_id_prefix: str = "",
        max_id_len: int | None = None,
    ) -> str:
        base = order_details.trading_pair.base
        quote = order_details.trading_pair.quote
        is_buy = order_details.trade_type == TradeType.BUY

        side = "B" if is_buy else "S"  # 1 char
        base_str = f"{base[0]}{base[-1]}"  # 2 chars
        quote_str = f"{quote[0]}{quote[-1]}"  # 2 chars
        ts_hex = hex(self._microseconds_nonce_provider.get_tracking_nonce())[2:]
        client_order_id = f"{client_operation_id_prefix}{side}{base_str}{quote_str}{ts_hex}{self._client_instance_id}"

        if max_id_len is not None:
            id_prefix = f"{client_operation_id_prefix}{side}{base_str}{quote_str}"
            suffix_max_length = max_id_len - len(id_prefix)
            if suffix_max_length < len(ts_hex):
                id_suffix = md5(
                    f"{ts_hex}{self._client_instance_id}".encode()
                ).hexdigest()
                client_order_id = f"{id_prefix}{id_suffix[:suffix_max_length]}"
            else:
                client_order_id = client_order_id[:max_id_len]
        return client_order_id

    def place_order(
        self,
        account: Owner,
        order_details: OrderDetails,
        client_operation_id_prefix: str = "",
    ) -> str:
        client_order_id = self.get_new_client_operation_id(
            order_details, client_operation_id_prefix=client_operation_id_prefix
        )
        self._create_order(account, client_order_id, order_details)
        return client_order_id

    @abstractmethod
    def start_tracking_order(
        self, account: Owner, client_order_id: str, order_details: OrderDetails
    ) -> None:
        raise NotImplementedError

    def prepare_order_details(self, order_details: OrderDetails) -> OrderDetails:
        return order_details

    def _create_order(
        self, account: Owner, client_order_id: str, order_details: OrderDetails
    ) -> None:
        order_details = self.prepare_order_details(order_details)

        self.start_tracking_order(
            account,
            client_order_id,
            order_details,
        )

        asyncio.ensure_future(
            self._request_create_order(
                account=account,
                client_order_id=client_order_id,
                order_details=order_details,
            )
        )

    async def _request_create_order(
        self, account: Owner, client_order_id: str, order_details: OrderDetails
    ) -> tuple[str, str | None]:
        exchange_order_id = None
        try:
            try:
                order_details.check_potential_failure(self.current_timestamp)
            except Exception as e:
                self._update_order_after_failure(
                    account, client_order_id, order_details, exception=e
                )
                return client_order_id, exchange_order_id

            exchange_order_id, update_timestamp = await self._place_order(
                account, client_order_id, order_details
            )
            new_state = (
                OrderState.OPEN
                if self.is_create_request_in_exchange_synchronous
                else OrderState.PENDING_CREATE
            )

            order_update: OrderUpdate = OrderUpdate(
                client_order_id=client_order_id,
                exchange_order_id=exchange_order_id,
                trading_pair=order_details.trading_pair,
                update_timestamp=update_timestamp,
                new_state=new_state,
            )
            self.process_order_update(account, order_update)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._update_order_after_failure(
                account, client_order_id, order_details, exception=e
            )
        return client_order_id, exchange_order_id

    @abstractmethod
    async def _place_order(
        self,
        account: Owner,
        client_order_id: str,
        order_details: OrderDetails,
    ) -> tuple[str, float]:
        raise NotImplementedError

    def _update_order_after_failure(
        self,
        account: Owner,
        client_order_id: str,
        order_details: OrderDetails,
        exception: Exception | None = None,
    ) -> None:
        if exception is not None:
            self.logger().error(f"Error placing order {client_order_id}: {exception}")

        order_update: OrderUpdate = OrderUpdate(
            client_order_id=client_order_id,
            trading_pair=order_details.trading_pair,
            update_timestamp=self.current_timestamp,
            new_state=OrderState.FAILED,
        )
        self.process_order_update(account, order_update)

    @abstractmethod
    def process_order_update(self, account: Owner, order_update: OrderUpdate) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_tracked_order(self, account: Owner, order_id: str) -> OrderOperation | None:
        raise NotImplementedError

    @abstractmethod
    def process_order_not_found(self, account: Owner, order: OrderOperation) -> None:
        raise NotImplementedError

    @abstractmethod
    def process_order_cancel_failure(
        self, account: Owner, order: OrderOperation
    ) -> None:
        raise NotImplementedError

    # === Cancel Functions ===

    def cancel(self, account: Owner, order_id: str) -> None:
        asyncio.ensure_future(self._execute_cancel(account, order_id))

    async def _execute_cancel(self, account: Owner, order_id: str) -> None:
        tracked_order = self.get_tracked_order(account, order_id)
        if tracked_order is not None:
            await self._execute_order_cancel(account, tracked_order)

    async def _execute_order_cancel(
        self, account: Owner, order: OrderOperation
    ) -> None:
        cancelled = False
        try:
            cancelled = await self._place_cancel(account, order)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            # WARNING: Binance does not allow cancels with the client/user order id so log a warning and wait for the creation of the order to complete
            self.logger().warning(
                f"Failed to cancel the order {order.client_operation_id} because it does not have an exchange order id yet"
            )
            self.process_order_not_found(account, order)
        except Exception:
            self.logger().error(
                f"Failed to cancel order {order.client_operation_id}", exc_info=True
            )

            order_update: OrderUpdate = OrderUpdate(
                client_order_id=order.client_operation_id,
                trading_pair=order.trading_pair,
                update_timestamp=self.current_timestamp,
                new_state=(
                    OrderState.CANCELED
                    if self.is_cancel_request_in_exchange_synchronous
                    else OrderState.PENDING_CANCEL
                ),
            )
            self.process_order_update(account, order_update)

        if not cancelled:
            self.process_order_cancel_failure(account, order)

    @abstractmethod
    async def _place_cancel(
        self, account: Owner, tracked_order: OrderOperation
    ) -> bool:
        raise NotImplementedError

    def cancel_batch(self, account: Owner, order_ids: list[str]) -> None:
        asyncio.ensure_future(self._place_batch_cancel(account, order_ids))

    async def _place_batch_cancel(self, account: Owner, order_ids: list[str]) -> None:
        tasks = [self._execute_cancel(account, order_id) for order_id in order_ids]
        await asyncio.gather(*tasks, return_exceptions=True)
