import time
from collections.abc import Callable
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel

from financepype.markets.trading_pair import TradingPair


class FundingPaymentType(Enum):
    """Enumeration of funding payment types for perpetual contracts.

    - NEXT: Next funding payment period
    - LAST: Last funding payment period
    """

    NEXT = "NEXT"
    LAST = "LAST"


class FundingInfoUpdate(BaseModel):
    """Update information for funding rates and prices.

    This class represents an update to funding-related information for a perpetual
    contract, including prices and funding rates.

    Attributes:
        trading_pair (TradingPair): The trading pair identifier
        index_price (Decimal | None): Updated index price
        mark_price (Decimal | None): Updated mark price
        next_funding_utc_timestamp (int | None): Next funding time in UTC
        next_funding_rate (Decimal | None): Next funding rate
        last_funding_rate (Decimal | None): Last funding rate
    """

    trading_pair: TradingPair
    index_price: Decimal | None = None
    mark_price: Decimal | None = None
    next_funding_utc_timestamp: int | None = None
    next_funding_rate: Decimal | None = None
    last_funding_rate: Decimal | None = None


class FundingPayment(BaseModel):
    """Represents a funding payment for a perpetual contract.

    This class models individual funding payments that occur in perpetual contracts,
    including the amount, direction, and timing of the payment.

    Attributes:
        trading_pair (TradingPair): The trading pair involved
        amount (Decimal): Payment amount
        is_received (bool): Whether payment was received (True) or paid (False)
        timestamp (int): When the payment occurred
        settlement_token (str): Token used for settlement
        funding_id (str): Unique identifier for the payment
        exchange_symbol (str | None): Exchange-specific symbol
    """

    trading_pair: TradingPair
    amount: Decimal
    is_received: bool
    timestamp: int
    settlement_token: str
    funding_id: str
    exchange_symbol: str | None = None

    @property
    def signed_amount(self) -> Decimal:
        """Get the signed amount of the funding payment.

        Returns:
            Decimal: Positive for received payments, negative for paid payments
        """
        return self.amount if self.is_received else -self.amount


class FundingInfo(BaseModel):
    """Information about funding for a perpetual market.

    This class contains comprehensive information about the funding state of a
    perpetual contract market, including current rates, timestamps, and payment
    schedules.

    Attributes:
        trading_pair (TradingPair): The trading pair
        index_price (Decimal): Current index price
        mark_price (Decimal): Current mark price
        next_funding_utc_timestamp (int | None): Next funding time
        next_funding_rate (Decimal): Next funding rate as percentage
        last_funding_utc_timestamp (int | None): Last funding time
        last_funding_rate (Decimal): Last funding rate as percentage
        payment_type (FundingPaymentType): Type of payment (NEXT/LAST)
        live_payment_frequency (int | None): Frequency of live payments
        utc_timestamp (int | None): Current timestamp
    """

    trading_pair: TradingPair
    index_price: Decimal
    mark_price: Decimal
    next_funding_utc_timestamp: int | None
    next_funding_rate: Decimal  # percentage
    last_funding_utc_timestamp: int | None
    last_funding_rate: Decimal  # percentage
    payment_type: FundingPaymentType
    live_payment_frequency: int | None = None
    utc_timestamp: int | None = None

    @property
    def payment_seconds_interval(self) -> int | None:
        """Calculate the interval between funding payments.

        Returns:
            int | None: Interval in seconds between payments, or None if not available
        """
        if (
            self.next_funding_utc_timestamp is not None
            and self.last_funding_utc_timestamp is not None
        ):
            return self.next_funding_utc_timestamp - self.last_funding_utc_timestamp
        return None

    @property
    def has_live_payments(self) -> bool:
        """Check if the market has live funding payments.

        Returns:
            bool: True if live payments are enabled
        """
        return self.live_payment_frequency is not None

    def update(self, info_update: "FundingInfoUpdate") -> None:
        """Update funding information with new data.

        This method updates the funding information with new values while
        maintaining the history of funding rates.

        Args:
            info_update (FundingInfoUpdate): New funding information
        """
        update_dict = info_update.model_dump(exclude_unset=True)
        update_dict.pop("trading_pair", None)
        for key, value in update_dict.items():
            if value is not None:
                if key == "next_funding_utc_timestamp":
                    if (
                        value is not None
                        and self.next_funding_utc_timestamp is not None
                        and value > self.next_funding_utc_timestamp
                    ):
                        self.last_funding_utc_timestamp = (
                            self.next_funding_utc_timestamp
                        )
                setattr(self, key, value)

    def get_next_payment_rates(
        self,
        payment_seconds_format: int | None = None,
        closing_time: int | None = None,
        current_time_function: Callable[[], float] = time.time,
    ) -> dict[int, Decimal] | None:
        """Calculate future funding payment rates.

        This method calculates the expected funding payments up to a specified time,
        taking into account live payment frequency if enabled.

        Args:
            payment_seconds_format (int | None): Custom payment interval in seconds
            closing_time (int | None): Time until which to calculate payments
            current_time_function (Callable[[], float]): Function to get current time

        Returns:
            dict[int, Decimal] | None: Map of payment timestamps to rates, or None if
                calculation is not possible
        """

        # If the closing time is after the next funding time, we cannot estimate the payments after and therefore we respond with None (error)
        if (
            closing_time is not None
            and self.next_funding_utc_timestamp is not None
            and closing_time > self.next_funding_utc_timestamp
        ):
            return None

        if self.payment_seconds_interval is None:
            return None

        # Calculate the format and normalized rate
        output_seconds_format: int = (
            payment_seconds_format
            if payment_seconds_format is not None
            else self.payment_seconds_interval
        )
        last_payment = closing_time or self.next_funding_utc_timestamp
        if last_payment is None:
            return None

        rate = (
            self.next_funding_rate
            if self.payment_type == FundingPaymentType.NEXT
            else self.last_funding_rate
        )
        rate = (rate / self.payment_seconds_interval) * output_seconds_format
        payments = {}

        # In case the funding is live, we need to calculate the payments for the live funding
        if self.live_payment_frequency is not None:
            first_payment = (
                current_time_function()
                // self.live_payment_frequency
                * self.live_payment_frequency
            ) + self.live_payment_frequency
            rate = rate / (self.payment_seconds_interval // self.live_payment_frequency)
            for time in range(
                int(first_payment), int(last_payment), self.live_payment_frequency
            ):
                payments[time] = rate

        # Add the last payment if it is the same as the next funding time
        if (
            self.next_funding_utc_timestamp is not None
            and last_payment == self.next_funding_utc_timestamp
        ):
            payments[last_payment] = rate
        return payments
