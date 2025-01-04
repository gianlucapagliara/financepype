from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from financepype.constants import s_decimal_0
from financepype.markets.candle import Candle, CandleTimeframe, CandleType


@pytest.fixture
def base_time() -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def sample_candle(base_time: datetime) -> Candle:
    return Candle(
        start_time=base_time,
        end_time=base_time + timedelta(minutes=1),
        open=Decimal("50000.00"),
        close=Decimal("50100.00"),
        high=Decimal("50200.00"),
        low=Decimal("49900.00"),
        volume=Decimal("10.5"),
    )


def test_candle_timeframe_values() -> None:
    """Test that CandleTimeframe enum has correct values."""
    assert CandleTimeframe.SEC_1.value == 1
    assert CandleTimeframe.MIN_1.value == 60
    assert CandleTimeframe.MIN_5.value == 300
    assert CandleTimeframe.MIN_15.value == 900
    assert CandleTimeframe.MIN_30.value == 1800
    assert CandleTimeframe.HOUR_1.value == 3600
    assert CandleTimeframe.HOUR_2.value == 7200
    assert CandleTimeframe.HOUR_4.value == 14400
    assert CandleTimeframe.DAY_1.value == 86400
    assert CandleTimeframe.WEEK_1.value == 604800
    assert CandleTimeframe.MONTH_1.value == 2592000


def test_candle_type_values() -> None:
    """Test that CandleType enum has correct values."""
    assert CandleType.PRICE.value == "PRICE"
    assert CandleType.MARK.value == "MARK"
    assert CandleType.INDEX.value == "INDEX"
    assert CandleType.PREMIUM.value == "PREMIUM"
    assert CandleType.FUNDING.value == "FUNDING"
    assert CandleType.ACCRUED_FUNDING.value == "ACCRUED_FUNDING"


def test_candle_initialization(sample_candle: Candle) -> None:
    """Test successful initialization of Candle with valid data."""
    assert sample_candle.start_time == datetime(2024, 1, 1, 12, 0, 0)
    assert sample_candle.end_time == datetime(2024, 1, 1, 12, 1, 0)
    assert sample_candle.open == Decimal("50000.00")
    assert sample_candle.close == Decimal("50100.00")
    assert sample_candle.high == Decimal("50200.00")
    assert sample_candle.low == Decimal("49900.00")
    assert sample_candle.volume == Decimal("10.5")


def test_fill_missing_candles_empty_list(base_time: datetime) -> None:
    """Test filling missing candles with an empty list."""
    result = Candle.fill_missing_candles_with_prev_candle(
        [], base_time, base_time + timedelta(minutes=5)
    )
    assert result == []


def test_fill_missing_candles_no_gaps(base_time: datetime) -> None:
    """Test filling missing candles when there are no gaps."""
    candles = [
        Candle(
            start_time=base_time + timedelta(minutes=i),
            end_time=base_time + timedelta(minutes=i + 1),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        )
        for i in range(5)
    ]
    result = Candle.fill_missing_candles_with_prev_candle(
        candles, base_time, base_time + timedelta(minutes=5)
    )
    assert len(result) == 5
    assert result == candles[::-1]  # Result should be reversed


def test_fill_missing_candles_with_gaps(base_time: datetime) -> None:
    """Test filling missing candles when there are gaps."""
    candles = [
        Candle(
            start_time=base_time,
            end_time=base_time + timedelta(minutes=1),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        ),
        Candle(
            start_time=base_time + timedelta(minutes=3),
            end_time=base_time + timedelta(minutes=4),
            open=Decimal("50300.00"),
            close=Decimal("50400.00"),
            high=Decimal("50500.00"),
            low=Decimal("50200.00"),
            volume=Decimal("12.5"),
        ),
    ]
    result = Candle.fill_missing_candles_with_prev_candle(
        candles, base_time, base_time + timedelta(minutes=4)
    )
    assert len(result) == 4
    # Check that the gap is filled with the previous candle's close price
    assert result[1].close == candles[0].close
    assert result[1].volume == s_decimal_0


def test_fill_missing_candles_before_start(base_time: datetime) -> None:
    """Test filling missing candles before the first candle."""
    candles = [
        Candle(
            start_time=base_time + timedelta(minutes=2),
            end_time=base_time + timedelta(minutes=3),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        ),
    ]
    result = Candle.fill_missing_candles_with_prev_candle(
        candles, base_time, base_time + timedelta(minutes=3)
    )
    assert len(result) == 3
    # Check that the missing candles before the first one are filled
    assert result[2].start_time == base_time
    assert result[2].end_time == base_time + timedelta(minutes=1)
    assert result[2].open == candles[0].open
    assert result[2].close == candles[0].open
    assert result[2].volume == s_decimal_0


def test_convert_candles_interval_same_interval(base_time: datetime) -> None:
    """Test converting candles when target interval is the same."""
    candles = [
        Candle(
            start_time=base_time + timedelta(minutes=i),
            end_time=base_time + timedelta(minutes=i + 1),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        )
        for i in range(5)
    ]
    result = Candle.convert_candles_interval(candles, 60)  # 1 minute interval
    assert len(result) == 5
    assert result == candles


def test_convert_candles_interval_aggregate(base_time: datetime) -> None:
    """Test converting candles to a larger interval."""
    candles = [
        Candle(
            start_time=base_time + timedelta(minutes=i),
            end_time=base_time + timedelta(minutes=i + 1),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        )
        for i in range(5)
    ]
    result = Candle.convert_candles_interval(candles, 300)  # 5 minute interval
    assert len(result) == 1
    assert result[0].start_time == base_time
    assert result[0].end_time == base_time + timedelta(minutes=5)
    assert result[0].open == candles[0].open
    assert result[0].close == candles[-1].close
    assert result[0].high == max(c.high for c in candles)
    assert result[0].low == min(c.low for c in candles)
    # Sum volumes, treating None as 0
    total_volume = sum((c.volume or s_decimal_0) for c in candles)
    assert result[0].volume == total_volume


def test_convert_candles_interval_invalid_target(base_time: datetime) -> None:
    """Test converting candles to an invalid target interval."""
    candles = [
        Candle(
            start_time=base_time + timedelta(minutes=i),
            end_time=base_time + timedelta(minutes=i + 1),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        )
        for i in range(5)
    ]
    # Try to convert 1-minute candles (60 seconds) to 90-second candles (not a multiple)
    with pytest.raises(
        ValueError, match="Cannot aggregate candles with a non multiple interval"
    ):
        Candle.convert_candles_interval(
            candles, 90
        )  # 90 seconds is not a multiple of 60 seconds


def test_convert_candles_interval_different_intervals(base_time: datetime) -> None:
    """Test converting candles with different intervals."""
    candles = [
        Candle(
            start_time=base_time,
            end_time=base_time + timedelta(minutes=1),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        ),
        Candle(
            start_time=base_time + timedelta(minutes=1),
            end_time=base_time + timedelta(minutes=3),  # Different interval
            open=Decimal("50100.00"),
            close=Decimal("50200.00"),
            high=Decimal("50300.00"),
            low=Decimal("50000.00"),
            volume=Decimal("11.5"),
        ),
    ]
    with pytest.raises(ValueError, match="Candles have different intervals"):
        Candle.convert_candles_interval(candles, 300)


def test_convert_candles_interval_bigger_target(base_time: datetime) -> None:
    """Test converting candles to a bigger interval than source."""
    candles = [
        Candle(
            start_time=base_time + timedelta(minutes=i * 5),
            end_time=base_time + timedelta(minutes=(i + 1) * 5),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        )
        for i in range(5)
    ]
    with pytest.raises(
        ValueError, match="Cannot aggregate candles with a bigger interval"
    ):
        Candle.convert_candles_interval(candles, 60)  # Try to convert 5min to 1min


def test_convert_candles_interval_partial_aggregate(base_time: datetime) -> None:
    """Test converting candles where the last group is incomplete."""
    candles = [
        Candle(
            start_time=base_time + timedelta(minutes=i),
            end_time=base_time + timedelta(minutes=i + 1),
            open=Decimal("50000.00"),
            close=Decimal("50100.00"),
            high=Decimal("50200.00"),
            low=Decimal("49900.00"),
            volume=Decimal("10.5"),
        )
        for i in range(7)  # 7 one-minute candles
    ]
    result = Candle.convert_candles_interval(candles, 300)  # 5 minute interval
    assert len(result) == 2  # Should get one complete 5-min candle and one partial
    assert result[0].start_time == base_time
    assert result[0].end_time == base_time + timedelta(minutes=5)
    assert result[1].start_time == base_time + timedelta(minutes=5)
    assert result[1].end_time == base_time + timedelta(minutes=10)
