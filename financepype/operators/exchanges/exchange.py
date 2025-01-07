import asyncio
from abc import abstractmethod
from decimal import Decimal
from hashlib import md5

from bidict import bidict

from financepype.constants import s_decimal_0, s_decimal_min, s_decimal_NaN
from financepype.operations.orders.models import OrderModifier, OrderType, TradeType
from financepype.operations.orders.order import OrderOperation, OrderState, OrderUpdate
from financepype.operators.operator import Operator
from financepype.owners.owner import Owner
from financepype.platforms.platform import Platform
from financepype.rules.trading_rule import TradingRule
from financepype.rules.trading_rules_tracker import TradingRulesTracker
from financepype.simulations.balances.engines.models import OrderDetails


class Exchange(Operator):
    def __init__(self, platform: Platform):
        super().__init__(platform)

        self._trading_rules_tracker: TradingRulesTracker | None = None
        self._trading_pairs: list[str] = []

        self.init_trading_rules_tracker()

    # === Properties ===

    @property
    def trading_rules(self) -> dict[str, TradingRule]:
        if self.trading_rules_tracker is None:
            return {}
        return self.trading_rules_tracker.trading_rules

    @property
    def trading_rules_tracker(self) -> TradingRulesTracker | None:
        return self._trading_rules_tracker

    @property
    def trading_pairs(self) -> list[str]:
        return self._trading_pairs

    @property
    @abstractmethod
    def supported_order_types(self) -> list[OrderType]:
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_order_modifiers(self) -> list[OrderModifier]:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_create_request_in_exchange_synchronous(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        raise NotImplementedError

    # === Core Functions ===

    def tick(self, timestamp: float) -> None:
        super().tick(timestamp)

    def start(self, timestamp: float) -> None:
        super().start(timestamp)

    def stop(self) -> None:
        super().stop()

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

    async def trading_pair_symbol_map(self) -> bidict[str, str]:
        if self.trading_rules_tracker is None:
            return bidict()
        return await self.trading_rules_tracker.trading_pair_symbol_map()

    def trading_pair_symbol_map_ready(self) -> bool:
        if self.trading_rules_tracker is None:
            return False
        return self.trading_rules_tracker.is_ready

    async def all_trading_pairs(self) -> list[str]:
        if self.trading_rules_tracker is None:
            return []
        return await self.trading_rules_tracker.all_trading_pairs()

    async def all_exchange_symbols(self) -> list[str]:
        if self.trading_rules_tracker is None:
            return []
        return await self.trading_rules_tracker.all_exchange_symbols()

    async def exchange_symbol_associated_to_pair(self, trading_pair: str) -> str:
        if self.trading_rules_tracker is None:
            return trading_pair
        return await self.trading_rules_tracker.exchange_symbol_associated_to_pair(
            trading_pair
        )

    async def is_trading_pair_valid(self, trading_pair: str) -> bool:
        if self.trading_rules_tracker is None:
            return False
        return await self.trading_rules_tracker.is_trading_pair_valid(trading_pair)

    async def trading_pair_associated_to_exchange_symbol(self, symbol: str) -> str:
        if self.trading_rules_tracker is None:
            return symbol
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
        self, trading_pair: str, is_buy: bool, amount: Decimal = s_decimal_NaN
    ) -> Decimal:
        """
        Get price for the market trading pair.
        :param trading_pair: The market trading pair
        :param is_buy: Whether to buy or sell the underlying asset
        :param amount: The amount (to buy or sell) (optional)
        :returns The price
        """
        raise NotImplementedError

    @abstractmethod
    def get_quote_price(
        self, trading_pair: str, is_buy: bool, amount: Decimal
    ) -> Decimal:
        """
        Returns a quote price (or exchange rate) for a given amount, like asking how much does it cost to buy 4 apples?
        :param trading_pair: The market trading pair
        :param is_buy: True for buy order, False for sell order
        :param amount: The order amount
        :return The quoted price
        """
        raise NotImplementedError

    @abstractmethod
    def get_order_price(
        self, trading_pair: str, is_buy: bool, amount: Decimal
    ) -> Decimal:
        """
        Returns a price required for order submission, this price could differ from the quote price (e.g. for
        an exchange with order book).
        :param trading_pair: The market trading pair
        :param is_buy: True for buy order, False for sell order
        :param amount: The order amount
        :return The price to specify in an order.
        """
        raise NotImplementedError

    def get_order_price_quantum(
        self, trading_pair: str, price: Decimal = s_decimal_0
    ) -> Decimal:
        """
        Used by quantize_order_price() in _create_order()
        Returns a price step, a minimum price increment for a given trading pair.

        :param trading_pair: the trading pair to check for market conditions
        :param price: the starting point price
        """
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
        self, trading_pair: str, order_size: Decimal = s_decimal_0
    ) -> Decimal:
        """
        Used by quantize_order_price() in _create_order()
        Returns an order amount step, a minimum amount increment for a given trading pair.

        :param trading_pair: the trading pair to check for market conditions
        :param order_size: the starting point order price
        """
        trading_rule = self.trading_rules[trading_pair]
        return Decimal(trading_rule.min_base_amount_increment)

    def quantize_order_amount(
        self, trading_pair: str, amount: Decimal, price: Decimal = s_decimal_0
    ) -> Decimal:
        """
        Applies the trading rules to calculate the correct order amount for the market

        :param trading_pair: the token pair for which the order will be created
        :param amount: the intended amount for the order
        :param price: the intended price for the order

        :return: the quantized order amount after applying the trading rules
        """
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

    def _quantize_order_amount(self, trading_pair: str, amount: Decimal) -> Decimal:
        order_size_quantum = self.get_order_size_quantum(trading_pair, amount)
        return (amount // order_size_quantum) * order_size_quantum

    def _quantize_order_price(self, trading_pair: str, price: Decimal) -> Decimal:
        if price.is_nan():
            return price
        price_quantum = self.get_order_price_quantum(trading_pair, price)
        return (price // price_quantum) * price_quantum

    def quantize_order_price(
        self,
        trading_pair: str,
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

    def get_new_client_order_id(
        self,
        order_details: OrderDetails,
        client_order_id_prefix: str = "",
        max_id_len: int | None = None,
    ) -> str:
        base = order_details.trading_pair.base
        quote = order_details.trading_pair.quote
        is_buy = order_details.trade_type == TradeType.BUY

        side = "B" if is_buy else "S"  # 1 char
        base_str = f"{base[0]}{base[-1]}"  # 2 chars
        quote_str = f"{quote[0]}{quote[-1]}"  # 2 chars
        ts_hex = hex(self._microseconds_nonce_provider.get_tracking_nonce())[2:]
        client_order_id = f"{client_order_id_prefix}{side}{base_str}{quote_str}{ts_hex}{self._client_instance_id}"

        if max_id_len is not None:
            id_prefix = f"{client_order_id_prefix}{side}{base_str}{quote_str}"
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
        client_order_id_prefix: str = "",
    ) -> str:
        """
        Creates a promise to create a sell order using the parameters.
        :param trading_pair: the token pair to operate with
        :param amount: the order amount
        :param order_type: the type of order to create (MARKET, LIMIT, LIMIT_MAKER)
        :param price: the order price
        :param client_order_id_prefix: the prefix to add to the client order id
        :return: the id assigned by the connector to the order (the client id)
        """
        client_order_id = self.get_new_client_order_id(
            order_details, client_order_id_prefix=client_order_id_prefix
        )
        self._create_order(account, client_order_id, order_details)
        return client_order_id

    @abstractmethod
    def start_tracking_order(
        self, account: Owner, client_order_id: str, order_details: OrderDetails
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def prepare_order_details(self, order_details: OrderDetails) -> OrderDetails:
        raise NotImplementedError

    def _create_order(
        self, account: Owner, client_order_id: str, order_details: OrderDetails
    ) -> None:
        """
        Creates an order in the exchange using the parameters to configure it

        :param trade_type: the side of the order (BUY of SELL)
        :param order_id: the id that should be assigned to the order (the client id)
        :param trading_pair: the token pair to operate with
        :param amount: the order amount
        :param order_type: the type of order to create (MARKET, LIMIT, LIMIT_MAKER)
        :param price: the order price
        :param client_order_id_prefix: the prefix to add to the client order id
        """
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
    def get_tracked_order(self, order_id: str) -> OrderOperation | None:
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
        """
        Creates a promise to cancel an order in the exchange

        :param trading_pair: the trading pair the order to cancel operates with
        :param order_id: the client id of the order to cancel
        """
        asyncio.ensure_future(self._execute_cancel(account, order_id))

    async def _execute_cancel(self, account: Owner, order_id: str) -> None:
        """
        Requests the exchange to cancel an active order

        :param trading_pair: the trading pair the order to cancel operates with
        :param order_id: the client id of the order to cancel
        """
        tracked_order = self.get_tracked_order(order_id)
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
            # Binance does not allow cancels with the client/user order id so log a warning and wait for the creation of the order to complete
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
