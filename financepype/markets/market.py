from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Self, cast

from pydantic import BaseModel, Field, model_validator

FORMAT = "{str_base}-{str_quote}{str_type}{str_timeframe}{str_expiry}{str_price}{str_price_short}"


class InstrumentTimeframeType(Enum):
    """Enumeration of standard timeframes for financial instruments.

    Defines the standard timeframes used for trading instruments:
    - HOURLY: 1 hour period
    - BI_HOURLY: 2 hour period
    - QUART_HOURLY: 4 hour period
    - DAILY: 1 day period
    - BI_DAILY: 2 day period
    - WEEKLY: 1 week period
    - BI_WEEKLY: 2 week period
    - MONTHLY: 1 month period
    - BI_MONTHLY: 2 month period
    - QUARTERLY: 3 month period
    - BI_QUARTERLY: 6 month period
    - YEARLY: 1 year period
    - UNDEFINED: Undefined timeframe
    """

    HOURLY = "1H"
    BI_HOURLY = "2H"
    QUART_HOURLY = "4H"
    DAILY = "1D"
    BI_DAILY = "2D"
    WEEKLY = "1W"
    BI_WEEKLY = "2W"
    MONTHLY = "1M"
    BI_MONTHLY = "2M"
    QUARTERLY = "1Q"
    BI_QUARTERLY = "2Q"
    YEARLY = "1Y"
    UNDEFINED = "NA"


# Millisec time intervals, those with the months and quarter represent the max time possible
INSTRUMENT_TIMEFRAME_INTERVAL = OrderedDict(
    [
        (3600, InstrumentTimeframeType.HOURLY),
        (7200, InstrumentTimeframeType.BI_HOURLY),
        (14400, InstrumentTimeframeType.QUART_HOURLY),
        (86400, InstrumentTimeframeType.DAILY),
        (172800, InstrumentTimeframeType.BI_DAILY),
        (604800, InstrumentTimeframeType.WEEKLY),
        (1209600, InstrumentTimeframeType.BI_WEEKLY),
        (2678400, InstrumentTimeframeType.MONTHLY),  # Considering 31 days
        (
            5356800,
            InstrumentTimeframeType.BI_MONTHLY,
        ),  # Considering 31 + 31 days (like July + August)
        (
            7948800,
            InstrumentTimeframeType.QUARTERLY,
        ),  # Considering 31 + 31 + 30 days (Q3)
        (15897600, InstrumentTimeframeType.BI_QUARTERLY),  # Considering Q3 + Q4
        (31622400, InstrumentTimeframeType.YEARLY),  # Considering leap year
    ]
)


class InstrumentType(Enum):
    """Enumeration of financial instrument types.

    Defines the various types of financial instruments supported:
    - SPOT: Regular spot trading
    - FUTURE: Standard futures contracts
    - INVERSE_FUTURE: Inverse futures contracts
    - PERPETUAL: Perpetual futures contracts
    - INVERSE_PERPETUAL: Inverse perpetual futures
    - EQUITY: Equity instruments
    - CALL_OPTION: Standard call options
    - PUT_OPTION: Standard put options
    - INVERSE_CALL_OPTION: Inverse call options
    - INVERSE_PUT_OPTION: Inverse put options
    - CALL_SPREAD: Call option spreads
    - PUT_SPREAD: Put option spreads
    - VOLATILITY: Volatility instruments
    """

    SPOT = "SPOT"
    FUTURE = "FUTURE"
    INVERSE_FUTURE = "INVERSE_FUTURE"
    PERPETUAL = "PERPETUAL"
    INVERSE_PERPETUAL = "INVERSE_PERPETUAL"
    EQUITY = "EQUITY"
    CALL_OPTION = "CALL_OPTION"
    PUT_OPTION = "PUT_OPTION"
    INVERSE_CALL_OPTION = "INVERSE_CALL_OPTION"
    INVERSE_PUT_OPTION = "INVERSE_PUT_OPTION"
    CALL_SPREAD = "CALL_SPREAD"
    PUT_SPREAD = "PUT_SPREAD"
    VOLATILITY = "VOLATILITY"

    @property
    def is_spot(self) -> bool:
        """Check if the instrument is a spot trading instrument.

        Returns:
            bool: True if spot trading instrument, False otherwise
        """
        return self in [InstrumentType.SPOT]

    @property
    def is_derivative(self) -> bool:
        """Check if the instrument is a derivative.

        Returns:
            bool: True if derivative instrument, False otherwise
        """
        return not self.is_spot

    @property
    def is_perpetual(self) -> bool:
        """Check if the instrument is a perpetual contract.

        Returns:
            bool: True if perpetual contract, False otherwise
        """
        return self in [
            InstrumentType.PERPETUAL,
            InstrumentType.INVERSE_PERPETUAL,
            InstrumentType.EQUITY,
        ]

    @property
    def is_future(self) -> bool:
        """Check if the instrument is a futures contract.

        Returns:
            bool: True if futures contract, False otherwise
        """
        return self in [
            InstrumentType.FUTURE,
            InstrumentType.INVERSE_FUTURE,
        ]

    @property
    def is_option(self) -> bool:
        """Check if the instrument is an option contract.

        Returns:
            bool: True if option contract, False otherwise
        """
        return self in [
            InstrumentType.CALL_OPTION,
            InstrumentType.PUT_OPTION,
            InstrumentType.INVERSE_CALL_OPTION,
            InstrumentType.INVERSE_PUT_OPTION,
            InstrumentType.CALL_SPREAD,
            InstrumentType.PUT_SPREAD,
            InstrumentType.VOLATILITY,
        ]

    @property
    def is_inverse(self) -> bool:
        """Check if the instrument is an inverse contract.

        Returns:
            bool: True if inverse contract, False otherwise
        """
        return self in [
            InstrumentType.INVERSE_FUTURE,
            InstrumentType.INVERSE_PERPETUAL,
            InstrumentType.INVERSE_CALL_OPTION,
            InstrumentType.INVERSE_PUT_OPTION,
        ]

    @property
    def is_linear(self) -> bool:
        """Check if the instrument is a linear contract.

        Returns:
            bool: True if linear contract, False otherwise
        """
        return self in [
            InstrumentType.SPOT,
            InstrumentType.FUTURE,
            InstrumentType.PERPETUAL,
        ]


class MarketInfo(BaseModel):
    """Information about a trading market/instrument.

    This class contains all the relevant information about a trading instrument,
    including its base and quote currencies, type, timeframe, and other
    specifications.

    Attributes:
        base (str): Base currency or asset
        quote (str): Quote currency or asset
        instrument_type (InstrumentType): Type of the instrument
        timeframe_type (InstrumentTimeframeType | None): Timeframe for futures/options
        expiry_date (datetime | None): Expiration date for futures/options
        strike_price (Decimal | None): Strike price for options
        metadata (dict[str, Any]): Additional market-specific metadata
    """

    base: str
    quote: str
    instrument_type: InstrumentType
    timeframe_type: InstrumentTimeframeType | None = None
    expiry_date: datetime | None = None
    strike_price: Decimal | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        """Validate that required fields are present based on instrument type.

        Returns:
            Self: The validated instance

        Raises:
            ValueError: If required fields are missing for the instrument type
        """
        if self.instrument_type.is_option:
            if self.strike_price is None:
                raise ValueError("Strike price is required for options")
            if self.expiry_date is None:
                raise ValueError("Expiry date is required for options")
        elif self.instrument_type.is_future and self.expiry_date is None:
            raise ValueError("Expiry date is required for futures")
        return self

    @property
    def is_spot(self) -> bool:
        return self.instrument_type.is_spot

    @property
    def is_derivative(self) -> bool:
        return self.instrument_type.is_derivative

    @property
    def is_perpetual(self) -> bool:
        return self.instrument_type.is_perpetual

    @property
    def is_future(self) -> bool:
        return self.instrument_type.is_future

    @property
    def is_option(self) -> bool:
        return self.instrument_type.is_option

    @property
    def is_linear(self) -> bool:
        return self.instrument_type.is_linear

    @property
    def is_inverse(self) -> bool:
        return self.instrument_type.is_inverse

    @property
    def client_name(self) -> str:
        if self.is_spot:
            return f"{self.base}-{self.quote}"
        elif self.is_perpetual:
            return f"{self.base}-{self.quote}-{self.instrument_type.value}"
        elif self.is_option:
            timeframe_type = cast(InstrumentTimeframeType, self.timeframe_type)
            expiry_date = cast(datetime, self.expiry_date)
            return f"{self.base}-{self.quote}-{self.instrument_type.value}-{timeframe_type.value}-{expiry_date.strftime('%Y%m%d')}-{self.strike_price}"
        elif self.is_future:
            timeframe_type = cast(InstrumentTimeframeType, self.timeframe_type)
            return f"{self.base}-{self.quote}-{self.instrument_type.value}-{timeframe_type.value}"
        else:
            raise ValueError("Invalid instrument type")

    @classmethod
    def get_timeframe_type(
        cls,
        launch_timestamp: int,
        delivery_timestamp: int,
        instrument_timeframe_tolerance: int = 0,
        next_timeframe: bool = False,
    ) -> InstrumentTimeframeType:
        """Determine the timeframe type based on instrument duration.

        Args:
            launch_timestamp (int): Instrument launch timestamp
            delivery_timestamp (int): Instrument delivery/expiry timestamp
            instrument_timeframe_tolerance (int): Allowed tolerance in seconds
            next_timeframe (bool): Whether to get next larger timeframe

        Returns:
            InstrumentTimeframeType: The determined timeframe type
        """
        instrument_duration = delivery_timestamp - launch_timestamp
        if delivery_timestamp < 0:
            return InstrumentTimeframeType.UNDEFINED

        if not next_timeframe:
            for duration, timeframe_type in INSTRUMENT_TIMEFRAME_INTERVAL.items():
                if instrument_duration <= duration + instrument_timeframe_tolerance:
                    return timeframe_type
        else:
            for duration, timeframe_type in reversed(
                INSTRUMENT_TIMEFRAME_INTERVAL.items()
            ):
                if instrument_duration >= duration + instrument_timeframe_tolerance:
                    return timeframe_type

        return InstrumentTimeframeType.UNDEFINED

    @classmethod
    def split_client_instrument_name(cls, name: str) -> "MarketInfo":
        """Parse a client instrument name into its components.

        Parses a standardized instrument name string into a MarketInfo object.
        The name format should follow:
        {base}-{quote}{type}{timeframe}{expiry}{strike}

        Args:
            name (str): The instrument name to parse

        Returns:
            MarketInfo: Parsed market information

        Example:
            >>> MarketInfo.split_client_instrument_name("BTC-USD-FUTURE-1W-20240101")
        """
        split = name.split("-")

        base = split[0] if len(split) > 0 else ""
        quote = split[1] if len(split) > 1 else ""
        instrument_type = (
            InstrumentType(split[2]) if len(split) > 2 else InstrumentType.SPOT
        )
        timeframe_type = None
        expiry_date = None
        strike_price = None

        if instrument_type not in [
            InstrumentType.SPOT,
            InstrumentType.PERPETUAL,
            InstrumentType.INVERSE_PERPETUAL,
        ]:
            timeframe_type = (
                InstrumentTimeframeType(split[3])
                if len(split) > 3
                else InstrumentTimeframeType.UNDEFINED
            )
            expiry_date = (
                datetime.strptime(split[4], "%Y%m%d") if len(split) > 4 else None
            )
            if instrument_type in [
                InstrumentType.CALL_OPTION,
                InstrumentType.PUT_OPTION,
                InstrumentType.INVERSE_CALL_OPTION,
                InstrumentType.INVERSE_PUT_OPTION,
                InstrumentType.VOLATILITY,
            ]:
                strike_price = Decimal(split[5]) if len(split) > 5 else None

        return cls(
            base=base,
            quote=quote,
            instrument_type=instrument_type,
            timeframe_type=timeframe_type,
            expiry_date=expiry_date,
            strike_price=strike_price,
        )
