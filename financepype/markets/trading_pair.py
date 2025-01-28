from typing import Any, ClassVar

from pydantic import BaseModel, field_validator

from financepype.markets.market import InstrumentType, MarketInfo


class TradingPair(BaseModel):
    """A singleton class representing a trading pair in the system.

    This class implements the singleton pattern to ensure that only one instance
    of a trading pair with a specific name exists in the system at any time.
    Trading pairs are immutable and thread-safe.

    Attributes:
        name (str): The trading pair identifier in the format "BASE-QUOTE"
                   (e.g., "BTC-USDT", "ETH-USD")

    Example:
        >>> btc_usdt = TradingPair(name="BTC-USDT")
        >>> eth_usdt = TradingPair(name="ETH-USDT")
        >>> btc_usdt_2 = TradingPair(name="BTC-USDT")
        >>> assert btc_usdt is btc_usdt_2  # Same instance
    """

    name: str
    _instances: ClassVar[dict[str, "TradingPair"]] = {}

    def __new__(cls, **data: Any) -> "TradingPair":
        """Create or retrieve a TradingPair instance.

        Implements the singleton pattern to ensure only one instance exists
        per trading pair name.

        Args:
            **data: Keyword arguments including 'name' for the trading pair

        Returns:
            TradingPair: The singleton instance for the given name

        Raises:
            ValueError: If name is not provided
        """
        name = data.get("name")
        if not name:
            raise ValueError("Trading pair name is required")
        if name in cls._instances:
            return cls._instances[name]
        instance = super().__new__(cls)
        cls._instances[name] = instance
        return instance

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate the trading pair name format.

        Ensures the name follows the required format (BASE-QUOTE) and
        can be properly parsed into base and quote currencies.

        Args:
            v (str): The trading pair name to validate

        Returns:
            str: The validated name

        Raises:
            ValueError: If the name format is invalid
        """
        if not v or "-" not in v:
            raise ValueError(f"Invalid trading pair name: {v}")
        try:
            # This will raise an error if the name is invalid
            MarketInfo.split_client_instrument_name(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid trading pair name: {v}") from e

    @property
    def market_info(self) -> MarketInfo:
        """Get the instrument information for this trading pair.

        Returns:
            InstrumentInfo: Object containing parsed instrument details
        """
        return MarketInfo.split_client_instrument_name(self.name)

    @property
    def base(self) -> str:
        """Get the base currency of the trading pair.

        Returns:
            str: The base currency (e.g., 'BTC' in 'BTC-USDT')
        """
        return self.market_info.base

    @property
    def quote(self) -> str:
        """Get the quote currency of the trading pair.

        Returns:
            str: The quote currency (e.g., 'USDT' in 'BTC-USDT')
        """
        return self.market_info.quote

    @property
    def instrument_type(self) -> InstrumentType:
        """Get the type of instrument this trading pair represents.

        Returns:
            InstrumentType: The type of the trading instrument
        """
        return self.market_info.instrument_type

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"TradingPair(name={self.name})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.name == other
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.name)

    def __deepcopy__(self, memo: dict) -> "TradingPair":
        """Handle deep copying of the singleton instance.

        Since TradingPair is a singleton, deep copying should return the same instance.

        Args:
            memo: Dictionary of id to object mappings

        Returns:
            TradingPair: The same singleton instance
        """
        return self
