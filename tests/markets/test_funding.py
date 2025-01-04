from decimal import Decimal
from time import time

import pytest

from financepype.markets.funding import (
    FundingInfo,
    FundingInfoUpdate,
    FundingPayment,
    FundingPaymentType,
)
from financepype.markets.trading_pair import TradingPair


@pytest.fixture
def trading_pair() -> TradingPair:
    return TradingPair(name="BTC-USD")


@pytest.fixture
def base_time() -> int:
    return int(time())


@pytest.fixture
def funding_info(trading_pair: TradingPair, base_time: int) -> FundingInfo:
    return FundingInfo(
        trading_pair=trading_pair,
        index_price=Decimal("50000.00"),
        mark_price=Decimal("50100.00"),
        next_funding_utc_timestamp=base_time + 3600,  # 1 hour from now
        next_funding_rate=Decimal("0.001"),  # 0.1%
        last_funding_utc_timestamp=base_time,
        last_funding_rate=Decimal("0.0008"),  # 0.08%
        payment_type=FundingPaymentType.NEXT,
    )


@pytest.fixture
def funding_payment(trading_pair: TradingPair) -> FundingPayment:
    return FundingPayment(
        trading_pair=trading_pair,
        amount=Decimal("10.5"),
        is_received=True,
        timestamp=int(time()),
        settlement_token="USD",
        funding_id="123456",
        exchange_symbol="BTC-USD-PERP",
    )


def test_funding_payment_type_values() -> None:
    """Test that FundingPaymentType enum has correct values."""
    assert FundingPaymentType.NEXT.value == "NEXT"
    assert FundingPaymentType.LAST.value == "LAST"


def test_funding_info_update_initialization() -> None:
    """Test successful initialization of FundingInfoUpdate with valid data."""
    update = FundingInfoUpdate(
        trading_pair="BTC-USD",
        index_price=Decimal("50000.00"),
        mark_price=Decimal("50100.00"),
        next_funding_utc_timestamp=int(time()) + 3600,
        next_funding_rate=Decimal("0.001"),
        last_funding_rate=Decimal("0.0008"),
    )
    assert update.trading_pair == "BTC-USD"
    assert update.index_price == Decimal("50000.00")
    assert update.mark_price == Decimal("50100.00")
    assert update.next_funding_rate == Decimal("0.001")
    assert update.last_funding_rate == Decimal("0.0008")


def test_funding_payment_initialization(funding_payment: FundingPayment) -> None:
    """Test successful initialization of FundingPayment with valid data."""
    assert isinstance(funding_payment.trading_pair, TradingPair)
    assert funding_payment.amount == Decimal("10.5")
    assert funding_payment.is_received is True
    assert isinstance(funding_payment.timestamp, int)
    assert funding_payment.settlement_token == "USD"
    assert funding_payment.funding_id == "123456"
    assert funding_payment.exchange_symbol == "BTC-USD-PERP"


def test_funding_payment_signed_amount(funding_payment: FundingPayment) -> None:
    """Test signed_amount property of FundingPayment."""
    assert funding_payment.signed_amount == Decimal("10.5")

    # Test with is_received=False
    funding_payment.is_received = False
    assert funding_payment.signed_amount == Decimal("-10.5")


def test_funding_info_initialization(
    funding_info: FundingInfo, trading_pair: TradingPair, base_time: int
) -> None:
    """Test successful initialization of FundingInfo with valid data."""
    assert isinstance(funding_info.trading_pair, TradingPair)
    assert funding_info.index_price == Decimal("50000.00")
    assert funding_info.mark_price == Decimal("50100.00")
    assert funding_info.next_funding_utc_timestamp == base_time + 3600
    assert funding_info.next_funding_rate == Decimal("0.001")
    assert funding_info.last_funding_utc_timestamp == base_time
    assert funding_info.last_funding_rate == Decimal("0.0008")
    assert funding_info.payment_type == FundingPaymentType.NEXT


def test_funding_info_payment_seconds_interval(
    funding_info: FundingInfo, base_time: int
) -> None:
    """Test payment_seconds_interval property of FundingInfo."""
    assert funding_info.payment_seconds_interval == 3600  # 1 hour


def test_funding_info_has_live_payments(funding_info: FundingInfo) -> None:
    """Test has_live_payments property of FundingInfo."""
    assert funding_info.has_live_payments is False

    funding_info.live_payment_frequency = 60  # Every minute
    assert funding_info.has_live_payments is True


def test_funding_info_update(funding_info: FundingInfo) -> None:
    """Test update method of FundingInfo."""
    next_timestamp = (
        funding_info.next_funding_utc_timestamp
        if funding_info.next_funding_utc_timestamp is not None
        else 0
    )
    update = FundingInfoUpdate(
        trading_pair="BTC-USD",
        index_price=Decimal("51000.00"),
        mark_price=Decimal("51100.00"),
        next_funding_utc_timestamp=next_timestamp + 3600,
        next_funding_rate=Decimal("0.002"),
        last_funding_rate=Decimal("0.001"),
    )

    funding_info.update(update)
    assert funding_info.index_price == Decimal("51000.00")
    assert funding_info.mark_price == Decimal("51100.00")
    assert funding_info.next_funding_rate == Decimal("0.002")
    assert funding_info.last_funding_rate == Decimal("0.001")
    assert (
        funding_info.last_funding_utc_timestamp is not None
        and funding_info.next_funding_utc_timestamp is not None
        and funding_info.last_funding_utc_timestamp
        == funding_info.next_funding_utc_timestamp - 3600
    )


def test_get_next_payment_rates_basic(
    funding_info: FundingInfo, base_time: int
) -> None:
    """Test get_next_payment_rates method with basic scenario."""

    def mock_time() -> int:
        return base_time

    rates = funding_info.get_next_payment_rates(current_time_function=mock_time)
    assert rates is not None
    assert len(rates) == 1
    assert rates[base_time + 3600] == Decimal("0.001")  # Next funding rate


def test_get_next_payment_rates_with_closing_time(
    funding_info: FundingInfo, base_time: int
) -> None:
    """Test get_next_payment_rates method with closing time."""

    def mock_time() -> int:
        return base_time

    # Test with closing time before next funding
    rates = funding_info.get_next_payment_rates(
        closing_time=base_time + 1800,  # 30 minutes from base_time
        current_time_function=mock_time,
    )
    assert rates is not None
    assert len(rates) == 0  # No payments before closing time

    # Test with closing time after next funding
    rates = funding_info.get_next_payment_rates(
        closing_time=base_time + 7200,  # 2 hours from base_time
        current_time_function=mock_time,
    )
    assert rates is None  # Cannot estimate payments after next funding


def test_get_next_payment_rates_with_live_payments(
    funding_info: FundingInfo, base_time: int
) -> None:
    """Test get_next_payment_rates method with live payments."""

    def mock_time() -> int:
        return base_time

    funding_info.live_payment_frequency = 1800  # Every 30 minutes
    rates = funding_info.get_next_payment_rates(current_time_function=mock_time)
    assert rates is not None
    assert len(rates) == 3  # Two live payments plus the final funding payment

    # Get all timestamps and sort them
    timestamps = sorted(rates.keys())

    # Check that we have the expected number of payments
    assert len(timestamps) == 3

    # Check that the timestamps are properly spaced
    assert (
        timestamps[1] - timestamps[0] == 1800
    )  # 30 minutes between first two payments
    assert (
        timestamps[2] == funding_info.next_funding_utc_timestamp
    )  # Last payment is at funding time

    # Check that all rates are equal and correct
    expected_rate = Decimal("0.001") / 2  # Rate is divided by number of payments
    for timestamp in timestamps:
        assert rates[timestamp] == expected_rate


def test_get_next_payment_rates_with_custom_format(
    funding_info: FundingInfo, base_time: int
) -> None:
    """Test get_next_payment_rates method with custom payment format."""

    def mock_time() -> int:
        return base_time

    # Test with 30-minute format
    rates = funding_info.get_next_payment_rates(
        payment_seconds_format=1800,  # 30 minutes
        current_time_function=mock_time,
    )
    assert rates is not None
    assert len(rates) == 1
    assert rates[base_time + 3600] == Decimal("0.0005")  # Half of the original rate


def test_funding_info_payment_seconds_interval_none(funding_info: FundingInfo) -> None:
    """Test payment_seconds_interval property when timestamps are None."""
    funding_info.next_funding_utc_timestamp = None
    assert funding_info.payment_seconds_interval is None

    funding_info.next_funding_utc_timestamp = 1000
    funding_info.last_funding_utc_timestamp = None
    assert funding_info.payment_seconds_interval is None


def test_get_next_payment_rates_no_interval(funding_info: FundingInfo) -> None:
    """Test get_next_payment_rates when payment_seconds_interval is None."""
    funding_info.next_funding_utc_timestamp = None
    rates = funding_info.get_next_payment_rates()
    assert rates is None
