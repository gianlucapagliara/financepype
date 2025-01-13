from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from financepype.constants import s_decimal_0, s_decimal_max, s_decimal_min
from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import OrderModifier, OrderType


class TradingRule(BaseModel):
    """Trading rules and constraints for a specific trading pair.

    This class defines the trading parameters and limitations for a trading pair
    on a specific platform. It includes order size limits, price increments,
    supported order types, and other platform-specific rules.

    The rules ensure that all trading operations comply with exchange requirements
    and prevent invalid orders from being submitted. The class uses Pydantic for
    validation and provides sensible defaults for most parameters.

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
        supported_order_types (set[OrderType]): Set of supported order types
        supported_order_modifiers (set[OrderModifier]): Set of supported order modifiers
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
        >>> print(rule.supports_limit_orders)  # Check order type support
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
        """Serialize decimal values to strings.

        This method ensures that decimal values are properly serialized
        when the model is converted to JSON or other formats.

        Args:
            decimal_value (Decimal): The decimal value to serialize

        Returns:
            str: The string representation of the decimal
        """
        return str(decimal_value)

    # Core trading pair information
    trading_pair: TradingPair = Field(description="Trading pair these rules apply to")

    # Order size limits
    min_order_size: Decimal = Field(
        default=s_decimal_0,
        description="Minimum allowed order size in base currency",
    )
    max_order_size: Decimal = Field(
        default=s_decimal_max,
        description="Maximum allowed order size in base currency",
    )

    # Price and amount increments
    min_price_increment: Decimal = Field(
        default=s_decimal_min,
        description="Minimum price increment (tick size)",
    )
    min_price_significance: int = Field(
        default=0,
        description="Minimum number of significant digits in price",
    )
    min_base_amount_increment: Decimal = Field(
        default=s_decimal_min,
        description="Minimum increment for base currency amount",
    )
    min_quote_amount_increment: Decimal = Field(
        default=s_decimal_min,
        description="Minimum increment for quote currency amount",
    )

    # Notional value limits
    min_notional_size: Decimal = Field(
        default=s_decimal_0,
        description="Minimum order value in quote currency",
    )
    max_notional_size: Decimal = Field(
        default=s_decimal_max,
        description="Maximum order value in quote currency",
    )

    # Order type support
    supported_order_types: set[OrderType] = Field(
        default_factory=lambda: {OrderType.LIMIT, OrderType.MARKET},
        description="Set of supported order types",
    )
    supported_order_modifiers: set[OrderModifier] = Field(
        default_factory=lambda: {OrderModifier.POST_ONLY},
        description="Set of supported order modifiers",
    )

    # Collateral configuration
    buy_order_collateral_token: str | None = Field(
        default=None,
        description="Token used as collateral for buy orders",
    )
    sell_order_collateral_token: str | None = Field(
        default=None,
        description="Token used as collateral for sell orders",
    )

    # Additional configuration
    product_id: str | None = Field(
        default=None,
        description="Platform-specific product identifier",
    )
    is_live: bool = Field(
        default=True,
        description="Whether trading is currently enabled",
    )
    other_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional platform-specific rules",
    )

    @field_validator("trading_pair", mode="before")
    @classmethod
    def validate_trading_pair(cls, v: str | TradingPair) -> TradingPair:
        """Convert string trading pair to TradingPair object.

        This validator allows the trading_pair field to accept either a string
        in the format "BASE-QUOTE" or a TradingPair instance. If a string is
        provided, it will be converted to a TradingPair object.

        Args:
            v: String trading pair name or TradingPair instance

        Returns:
            TradingPair: The validated trading pair object

        Raises:
            ValueError: If the trading pair format is invalid
        """
        if isinstance(v, str):
            return TradingPair(name=v)
        return v

    @model_validator(mode="after")
    def fix_collateral_tokens(self) -> Self:
        """Set default collateral tokens if not specified.

        For buy orders: Uses quote currency as collateral
        For sell orders: Uses base currency as collateral

        This method ensures that collateral tokens are always set to valid
        values, using the trading pair's base and quote currencies as defaults.

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

        This is a convenience property that calls is_active() with no timestamp.

        Returns:
            bool: True if trading is active
        """
        return self.is_active()

    @property
    def started(self) -> bool:
        """Check if trading has started.

        This is a convenience property that calls is_started() with no timestamp.

        Returns:
            bool: True if trading has started
        """
        return self.is_started()

    @property
    def expired(self) -> bool:
        """Check if trading has expired.

        This is a convenience property that calls is_expired() with no timestamp.

        Returns:
            bool: True if trading has expired
        """
        return self.is_expired()

    def is_expired(self, timestamp: int | float | None = None) -> bool:
        """Check if trading has expired at a specific timestamp.

        For spot trading, this always returns False as spot markets don't expire.
        Derivative markets override this method to implement expiration logic.

        Args:
            timestamp: Optional timestamp to check against

        Returns:
            bool: False for spot trading (never expires)
        """
        return False

    def is_started(self, timestamp: int | float | None = None) -> bool:
        """Check if trading has started at a specific timestamp.

        For spot trading, this always returns True as spot markets are always
        available for trading. Derivative markets override this method to
        implement start time logic.

        Args:
            timestamp: Optional timestamp to check against

        Returns:
            bool: True for spot trading (always started)
        """
        return True

    def is_active(self, timestamp: int | float | None = None) -> bool:
        """Check if trading is active at a specific timestamp.

        For spot trading, this always returns True as spot markets are always
        active. Derivative markets override this method to implement their
        own activity checks.

        Args:
            timestamp: Optional timestamp to check against

        Returns:
            bool: True for spot trading (always active)
        """
        return True

    @property
    def supports_limit_orders(self) -> bool:
        """Check if limit orders are supported.

        Returns:
            bool: True if limit orders are supported
        """
        return OrderType.LIMIT in self.supported_order_types

    @property
    def supports_market_orders(self) -> bool:
        """Check if market orders are supported.

        Returns:
            bool: True if market orders are supported
        """
        return OrderType.MARKET in self.supported_order_types


class DerivativeTradingRule(TradingRule):
    """Trading rules for derivative instruments.

    Extends the base TradingRule to add support for derivative-specific
    attributes like expiry timestamps and underlying assets. Supports
    both perpetual and expiring derivatives.

    This class adds functionality for:
    - Tracking underlying assets and indices
    - Managing expiration timestamps
    - Supporting both linear and inverse derivatives
    - Handling strike prices for options

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
        >>> print(future.is_expired())  # False
    """

    @model_validator(mode="after")
    def fix_collateral_tokens(self) -> Self:
        """Set default collateral tokens if not specified.

        For linear instruments, uses quote currency as collateral
        For inverse instruments, uses base currency as collateral

        This method overrides the base class implementation to handle
        the different collateral requirements of linear and inverse
        derivative contracts.

        Returns:
            Self: The validated instance
        """
        if self.trading_pair.market_info.is_linear:
            if self.buy_order_collateral_token is None:
                self.buy_order_collateral_token = self.trading_pair.market_info.quote
            if self.sell_order_collateral_token is None:
                self.sell_order_collateral_token = self.trading_pair.market_info.quote
        elif self.trading_pair.market_info.is_inverse:
            if self.buy_order_collateral_token is None:
                self.buy_order_collateral_token = self.trading_pair.market_info.base
            if self.sell_order_collateral_token is None:
                self.sell_order_collateral_token = self.trading_pair.market_info.base
        return self

    @field_serializer("strike_price")
    def serialize_strike_price(self, strike_price: Decimal | None) -> str | None:
        """Serialize the strike price to a string.

        Args:
            strike_price (Decimal | None): The strike price to serialize

        Returns:
            str | None: String representation of the strike price, or None
        """
        return str(strike_price) if strike_price is not None else None

    # Derivative-specific attributes
    underlying: str | None = Field(
        default=None,
        description="Symbol of the underlying asset",
    )
    strike_price: Decimal | None = Field(
        default=None,
        description="Strike price for options",
    )
    start_timestamp: int | float = Field(
        default=0,
        description="When trading begins",
    )
    expiry_timestamp: int | float = Field(
        default=-1,
        description="When trading ends (-1 for perpetual)",
    )
    index_symbol: str | None = Field(
        default=None,
        description="Symbol of the index being tracked",
    )

    @property
    def perpetual(self) -> bool:
        """Check if this is a perpetual derivative.

        A perpetual derivative is one that never expires, indicated by
        an expiry_timestamp of -1.

        Returns:
            bool: True if this is a perpetual contract (never expires)
        """
        return self.expiry_timestamp == -1

    def is_expired(self, timestamp: int | float | None = None) -> bool:
        """Check if the derivative has expired.

        Perpetual derivatives never expire. For expiring derivatives,
        checks if the current or provided timestamp is past the
        expiration time.

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

        Checks if the current or provided timestamp is past the
        start time for this derivative.

        Args:
            timestamp: Optional timestamp to check against (uses current time if None)

        Returns:
            bool: True if trading has started
        """
        timestamp = timestamp or datetime.now().timestamp()
        return timestamp >= self.start_timestamp

    def is_active(self, timestamp: int | float | None = None) -> bool:
        """Check if trading is currently active.

        A derivative is active if:
        1. Trading has started
        2. The contract hasn't expired
        3. Trading is enabled (is_live is True)

        Args:
            timestamp: Optional timestamp to check against (uses current time if None)

        Returns:
            bool: True if trading is active
        """
        return (
            self.is_live
            and self.is_started(timestamp)
            and not self.is_expired(timestamp)
        )
