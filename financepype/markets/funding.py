import time
from collections.abc import Callable
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel

from financepype.markets.trading_pair import TradingPair


class FundingPaymentType(Enum):
    NEXT = "NEXT"
    LAST = "LAST"


class FundingInfoUpdate(BaseModel):
    trading_pair: str
    index_price: Decimal | None = None
    mark_price: Decimal | None = None
    next_funding_utc_timestamp: int | None = None
    next_funding_rate: Decimal | None = None
    last_funding_rate: Decimal | None = None


class FundingPayment(BaseModel):
    trading_pair: TradingPair
    amount: Decimal
    is_received: bool
    timestamp: int
    settlement_token: str
    funding_id: str
    exchange_symbol: str | None = None

    @property
    def signed_amount(self) -> Decimal:
        return self.amount if self.is_received else -self.amount


class FundingInfo(BaseModel):
    """
    Data object that details the funding information of a perpetual market.
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
        if (
            self.next_funding_utc_timestamp is not None
            and self.last_funding_utc_timestamp is not None
        ):
            return self.next_funding_utc_timestamp - self.last_funding_utc_timestamp
        return None

    @property
    def has_live_payments(self) -> bool:
        return self.live_payment_frequency is not None

    def update(self, info_update: "FundingInfoUpdate") -> None:
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
        """
        Calculate the payments for the next funding time and the closing time if provided.

        :param payment_seconds_format: The format of the payment in seconds. If not provided, the default is the payment_seconds_interval.
        :param closing_time: The closing time of the position. If not provided, the default is the next funding time.
        :param current_time_function: The function to get the current time. If not provided, the default is time.time.

        -------
        :return: A dictionary with the payment times as keys and the payment rates as values.
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
