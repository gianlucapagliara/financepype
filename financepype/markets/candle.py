from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import cast

from pydantic import BaseModel

from financepype.constants import s_decimal_0


class CandleTimeframe(Enum):
    """Enumeration of standard candle timeframes.

    Each timeframe is represented by its duration in seconds:
    - SEC_1: 1 second
    - MIN_1: 1 minute (60 seconds)
    - MIN_5: 5 minutes (300 seconds)
    - MIN_15: 15 minutes (900 seconds)
    - MIN_30: 30 minutes (1800 seconds)
    - HOUR_1: 1 hour (3600 seconds)
    - HOUR_2: 2 hours (7200 seconds)
    - HOUR_4: 4 hours (14400 seconds)
    - DAY_1: 1 day (86400 seconds)
    - WEEK_1: 1 week (604800 seconds)
    - MONTH_1: 1 month (2592000 seconds)
    """

    SEC_1 = 1
    MIN_1 = 60
    MIN_5 = 300
    MIN_15 = 900
    MIN_30 = 1800
    HOUR_1 = 3600
    HOUR_2 = 7200
    HOUR_4 = 14400
    DAY_1 = 86400
    WEEK_1 = 604800
    MONTH_1 = 2592000


class CandleType(Enum):
    """Enumeration of different types of candles.

    - PRICE: Regular price candles based on actual trades
    - MARK: Mark price candles (typically for derivatives)
    - INDEX: Index price candles
    - PREMIUM: Premium/discount candles showing difference between spot and derivatives
    - FUNDING: Funding rate candles for perpetual contracts
    - ACCRUED_FUNDING: Accumulated funding rate candles
    """

    PRICE = "PRICE"
    MARK = "MARK"
    INDEX = "INDEX"
    PREMIUM = "PREMIUM"
    FUNDING = "FUNDING"
    ACCRUED_FUNDING = "ACCRUED_FUNDING"


class Candle(BaseModel):
    """Represents a single candlestick in a financial chart.

    A candle represents price movement over a specific time period, including
    opening price, closing price, highest and lowest prices reached, and
    optionally the trading volume.

    Attributes:
        start_time (datetime): Start time of the candle period
        end_time (datetime): End time of the candle period
        open (Decimal): Opening price
        close (Decimal): Closing price
        high (Decimal): Highest price during the period
        low (Decimal): Lowest price during the period
        volume (Decimal | None): Trading volume during the period, if available
    """

    start_time: datetime
    end_time: datetime
    open: Decimal
    close: Decimal
    high: Decimal
    low: Decimal
    volume: Decimal | None = None

    @classmethod
    def fill_missing_candles_with_prev_candle(
        cls, candles: list["Candle"], start: datetime, end: datetime
    ) -> list["Candle"]:
        """Fill gaps in candle data by propagating values from previous candles.

        This method ensures a continuous series of candles by filling any missing
        periods with candles that copy the closing price of the previous candle.

        Args:
            candles (list[Candle]): List of existing candles
            start (datetime): Start time for the complete series
            end (datetime): End time for the complete series

        Returns:
            list[Candle]: Complete list of candles with gaps filled
        """
        # If there are no candles, return an empty list
        if len(candles) == 0:
            return []

        # Sort candles by start time
        candles.sort(key=lambda candle: candle.start_time)

        # If the first candle is missing propagate it from the first valid one
        first_candle = candles[0]
        ending_time = max(end, candles[-1].end_time)
        candle_time = first_candle.end_time - first_candle.start_time
        prev_start_time = first_candle.start_time - candle_time
        missing_first_candles = []
        while prev_start_time >= start:
            prev_candle = Candle(
                start_time=prev_start_time,
                end_time=first_candle.start_time,
                open=first_candle.open,
                close=first_candle.open,
                high=first_candle.open,
                low=first_candle.open,
                volume=s_decimal_0,
            )
            first_candle = prev_candle
            prev_start_time = first_candle.start_time - candle_time
            missing_first_candles.append(prev_candle)
        candles = missing_first_candles[::-1] + candles

        # Calculating the right amount of candles
        num_candles = int((ending_time - start) // candle_time)

        # If we have all the candles, we return them
        if len(candles) >= num_candles:
            return candles[::-1]

        # Calculating all candles
        all_candles = [first_candle]
        starting_time = first_candle.end_time
        curr_available_candle_index = 1

        # Fill all the missing candles
        for i in range(1, num_candles):
            if (
                curr_available_candle_index < len(candles)
                and candles[curr_available_candle_index].start_time == starting_time
            ):
                all_candles.append(candles[curr_available_candle_index])
                curr_available_candle_index += 1
            else:
                missing_candle = Candle(
                    start_time=starting_time,
                    end_time=starting_time + candle_time,
                    open=all_candles[i - 1].close,
                    close=all_candles[i - 1].close,
                    high=all_candles[i - 1].close,
                    low=all_candles[i - 1].close,
                    volume=s_decimal_0,
                )
                all_candles.append(missing_candle)
            starting_time += candle_time

        return all_candles

    @classmethod
    def _validate_candle_intervals(cls, candles: list["Candle"]) -> int:
        """Validate that all candles have the same time interval.

        Args:
            candles (list[Candle]): List of candles to validate

        Returns:
            int: The common interval in seconds

        Raises:
            ValueError: If no candles provided or if intervals are inconsistent
        """
        if not candles:
            raise ValueError("No candles provided")

        current_interval = (candles[0].end_time - candles[0].start_time).seconds

        for candle in candles[1:]:
            interval = (candle.end_time - candle.start_time).seconds
            if interval != current_interval:
                raise ValueError("Candles have different intervals")

        return current_interval

    @classmethod
    def _validate_target_interval(
        cls, current_interval: int, target_interval: int
    ) -> None:
        """Validate that the target interval is valid for conversion.

        Args:
            current_interval (int): Current candle interval in seconds
            target_interval (int): Target interval in seconds

        Raises:
            ValueError: If target interval is invalid for conversion
        """
        if current_interval == target_interval:
            return
        if current_interval > target_interval:
            raise ValueError("Cannot aggregate candles with a bigger interval")
        if target_interval % current_interval != 0:
            raise ValueError("Cannot aggregate candles with a non multiple interval")

    @classmethod
    def _aggregate_candle_data(
        cls, candles: list["Candle"], start_idx: int, end_time: datetime
    ) -> tuple[
        list[Decimal], list[Decimal], list[Decimal], list[Decimal], list[Decimal], int
    ]:
        """Aggregate data from multiple candles within a time window.

        Args:
            candles (list[Candle]): List of candles to aggregate
            start_idx (int): Starting index in the candles list
            end_time (datetime): End time for aggregation window

        Returns:
            tuple: Contains lists of opens, closes, highs, lows, volumes, and next index
        """
        opens: list[Decimal] = []
        closes: list[Decimal] = []
        highs: list[Decimal] = []
        lows: list[Decimal] = []
        volumes: list[Decimal] = []
        j = start_idx

        for j in range(start_idx, len(candles)):
            if candles[j].end_time <= end_time:
                opens.append(candles[j].open)
                closes.append(candles[j].close)
                highs.extend([candles[j].open, candles[j].close, candles[j].high])
                lows.extend([candles[j].open, candles[j].close, candles[j].low])
                # Only include non-None volumes
                if candles[j].volume is not None:
                    volumes.append(cast(Decimal, candles[j].volume))
            else:
                break

        return opens, closes, highs, lows, volumes, j

    @classmethod
    def convert_candles_interval(
        cls, candles: list["Candle"], seconds_interval: int
    ) -> list["Candle"]:
        """Convert candles to a different time interval.

        This method aggregates candles into larger timeframes or splits them into
        smaller ones, maintaining OHLCV integrity.

        Args:
            candles (list[Candle]): List of candles to convert
            seconds_interval (int): Target interval in seconds

        Returns:
            list[Candle]: Converted candles at the new interval

        Raises:
            ValueError: If conversion to target interval is not possible
        """
        current_interval = cls._validate_candle_intervals(candles)
        cls._validate_target_interval(current_interval, seconds_interval)

        if current_interval == seconds_interval:
            return candles

        # Sort candles by start time and prepare for aggregation
        candles = sorted(candles, key=lambda candle: candle.start_time)
        aggregated_candles = []
        i = 0

        while i < len(candles):
            aggregation_start_time = candles[i].start_time
            aggregation_end_time = aggregation_start_time + timedelta(
                seconds=seconds_interval
            )

            opens, closes, highs, lows, volumes, next_i = cls._aggregate_candle_data(
                candles, i, aggregation_end_time
            )

            # Calculate volume only if we have valid volumes
            aggregated_volume: Decimal | None = (
                sum(volumes, s_decimal_0) if volumes else None
            )

            aggregated_candles.append(
                Candle(
                    start_time=aggregation_start_time,
                    end_time=aggregation_end_time,
                    open=opens[0],
                    close=closes[-1],
                    high=max(highs),
                    low=min(lows),
                    volume=aggregated_volume,
                )
            )

            i = next_i
            if i == len(candles) - 1:
                break

        return aggregated_candles
