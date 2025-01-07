from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from financepype.constants import s_decimal_0, s_decimal_max, s_decimal_min
from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import OrderModifier, OrderType


class TradingRule(BaseModel):
    """Trading rules and constraints for a specific trading pair.

    This class defines the trading parameters and limitations for a trading pair
    on a specific platform. It includes order size limits, price increments,
    supported order types, and other platform-specific rules.

    Attributes:
        trading_pair (TradingPair): The trading pair these rules apply to
        min_order_size (Decimal): Minimum allowed order size in base currency
        max_order_size (Decimal): Maximum allowed order size in base currency
        min_price_increment (Decimal): Minimum price increment (tick size)
        min_price_significance (int): Minimum number of significant digits in price
        min_base_amount_increment (Decimal): Minimum increment for base currency amount
        min_quote_amount_increment (Decimal): Minimum increment for quote currency amount
        min_notional_size (Decimal): Minimum order value in quote currency
        max_notional_size (Decimal): Maximum order value in quote currency
        supports_limit_orders (bool): Whether limit orders are supported
        supports_market_orders (bool): Whether market orders are supported
        buy_order_collateral_token (str | None): Token used as collateral for buys
        sell_order_collateral_token (str | None): Token used as collateral for sells
        product_id (str | None): Platform-specific product identifier
        is_live (bool): Whether trading is currently enabled
        other_rules (dict): Additional platform-specific rules

    Example:
        >>> rule = TradingRule(
        ...     trading_pair=TradingPair(name="BTC-USDT"),
        ...     min_order_size=Decimal("0.001"),
        ...     min_price_increment=Decimal("0.01"),
        ...     min_notional_size=Decimal("10")
        ... )
        >>> print(rule.active)  # Check if trading is active
    """

    model_config = ConfigDict()

    @field_serializer(
        "min_order_size",
        "max_order_size",
        "min_price_increment",
        "min_base_amount_increment",
        "min_quote_amount_increment",
        "min_notional_size",
        "max_notional_size",
    )
    def serialize_decimal(self, decimal_value: Decimal) -> str:
        return str(decimal_value)

    trading_pair: TradingPair
    min_order_size: Decimal = Field(default=s_decimal_0)
    max_order_size: Decimal = Field(default=s_decimal_max)
    min_price_increment: Decimal = Field(default=s_decimal_min)
    min_price_significance: int = Field(default=0)
    min_base_amount_increment: Decimal = Field(default=s_decimal_min)
    min_quote_amount_increment: Decimal = Field(default=s_decimal_min)
    min_notional_size: Decimal = Field(default=s_decimal_0)
    max_notional_size: Decimal = Field(default=s_decimal_max)
    supported_order_types: set[OrderType] = Field(
        default_factory=lambda: {OrderType.LIMIT, OrderType.MARKET}
    )
    supported_order_modifiers: set[OrderModifier] = Field(
        default_factory=lambda: {OrderModifier.POST_ONLY}
    )
    buy_order_collateral_token: str | None = None
    sell_order_collateral_token: str | None = None
    product_id: str | None = None
    is_live: bool = Field(default=True)
    other_rules: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fix_collateral_tokens(self) -> Self:
        """Set default collateral tokens if not specified.

        For buy orders: Uses quote currency as collateral
        For sell orders: Uses base currency as collateral

        Returns:
            Self: The validated instance
        """
        if self.buy_order_collateral_token is None:
            self.buy_order_collateral_token = self.trading_pair.quote
        if self.sell_order_collateral_token is None:
            self.sell_order_collateral_token = self.trading_pair.base
        return self

    @property
    def active(self) -> bool:
        """Check if trading is currently active.

        Returns:
            bool: True if trading is active
        """
        return self.is_active()

    @property
    def started(self) -> bool:
        """Check if trading has started.

        Returns:
            bool: True if trading has started
        """
        return self.is_started()

    @property
    def expired(self) -> bool:
        """Check if trading has expired.

        Returns:
            bool: True if trading has expired
        """
        return self.is_expired()

    def is_expired(self, timestamp: int | float | None = None) -> bool:
        """Check if trading has expired at a specific timestamp.

        Args:
            timestamp: Optional timestamp to check against

        Returns:
            bool: False for spot trading (never expires)
        """
        return False

    def is_started(self, timestamp: int | float | None = None) -> bool:
        """Check if trading has started at a specific timestamp.

        Args:
            timestamp: Optional timestamp to check against

        Returns:
            bool: True for spot trading (always started)
        """
        return True

    def is_active(self, timestamp: int | float | None = None) -> bool:
        """Check if trading is active at a specific timestamp.

        Args:
            timestamp: Optional timestamp to check against

        Returns:
            bool: True for spot trading (always active)
        """
        return True

    @property
    def supports_limit_orders(self) -> bool:
        return OrderType.LIMIT in self.supported_order_types

    @property
    def supports_market_orders(self) -> bool:
        return OrderType.MARKET in self.supported_order_types


class DerivativeTradingRule(TradingRule):
    """Trading rules for derivative instruments.

    Extends the base TradingRule to add support for derivative-specific
    attributes like expiry timestamps and underlying assets. Supports
    both perpetual and expiring derivatives.

    Attributes:
        underlying (str | None): Symbol of the underlying asset
        strike_price (Decimal | None): Strike price for options
        start_timestamp (int | float): When trading begins
        expiry_timestamp (int | float): When trading ends (-1 for perpetual)
        index_symbol (str | None): Symbol of the index being tracked

    Example:
        >>> future = DerivativeTradingRule(
        ...     trading_pair=TradingPair(name="BTC-USDT-PERP"),
        ...     underlying="BTC",
        ...     index_symbol="BTC/USD",
        ...     expiry_timestamp=-1  # Perpetual
        ... )
        >>> print(future.perpetual)  # True
    """

    @model_validator(mode="after")
    def fix_collateral_tokens(self) -> Self:
        """Set default collateral tokens if not specified.

        For linear instruments, uses quote currency as collateral
        For inverse instruments, uses base currency as collateral

        Returns:
            Self: The validated instance
        """
        instrument_info = self.trading_pair.instrument_info
        if instrument_info.is_linear:
            if self.buy_order_collateral_token is None:
                self.buy_order_collateral_token = instrument_info.quote
            if self.sell_order_collateral_token is None:
                self.sell_order_collateral_token = instrument_info.quote
        elif instrument_info.is_inverse:
            if self.buy_order_collateral_token is None:
                self.buy_order_collateral_token = instrument_info.base
            if self.sell_order_collateral_token is None:
                self.sell_order_collateral_token = instrument_info.base
        return self

    @field_serializer("strike_price")
    def serialize_strike_price(self, strike_price: Decimal | None) -> str | None:
        return str(strike_price) if strike_price is not None else None

    underlying: str | None = None
    strike_price: Decimal | None = None
    start_timestamp: int | float = Field(default=0)
    expiry_timestamp: int | float = Field(default=-1)
    index_symbol: str | None = None

    @property
    def perpetual(self) -> bool:
        """Check if this is a perpetual derivative.

        Returns:
            bool: True if this is a perpetual contract (never expires)
        """
        return self.expiry_timestamp == -1

    def is_expired(self, timestamp: int | float | None = None) -> bool:
        """Check if the derivative has expired.

        Args:
            timestamp: Optional timestamp to check against (uses current time if None)

        Returns:
            bool: True if the derivative has expired
        """
        if self.perpetual:
            return False
        timestamp = timestamp or datetime.now().timestamp()
        return timestamp >= self.expiry_timestamp

    def is_started(self, timestamp: int | float | None = None) -> bool:
        """Check if trading has started.

        Args:
            timestamp: Optional timestamp to check against (uses current time if None)

        Returns:
            bool: True if trading has started
        """
        timestamp = timestamp or datetime.now().timestamp()
        return timestamp >= self.start_timestamp

    def is_active(self, timestamp: int | float | None = None) -> bool:
        """Check if trading is currently active.

        Trading is active if it has started and has not expired.

        Args:
            timestamp: Optional timestamp to check against (uses current time if None)

        Returns:
            bool: True if trading is active
        """
        timestamp = timestamp or datetime.now().timestamp()
        return self.is_started(timestamp) and not self.is_expired(timestamp)
