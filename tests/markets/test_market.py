from datetime import datetime
from decimal import Decimal

import pytest

from financepype.markets.market import (
    InstrumentTimeframeType,
    InstrumentType,
    MarketInfo,
)


def test_spot_market_info() -> None:
    info = MarketInfo(base="BTC", quote="USD", instrument_type=InstrumentType.SPOT)
    assert info.base == "BTC"
    assert info.quote == "USD"
    assert info.instrument_type.is_spot
    assert not info.instrument_type.is_derivative


def test_perpetual_market_info() -> None:
    info = MarketInfo(base="BTC", quote="USD", instrument_type=InstrumentType.PERPETUAL)
    assert info.is_derivative
    assert info.is_perpetual
    assert not info.is_option


def test_option_market_info() -> None:
    expiry = datetime(2024, 1, 1)
    info = MarketInfo(
        base="BTC",
        quote="USD",
        instrument_type=InstrumentType.CALL_OPTION,
        timeframe_type=InstrumentTimeframeType.WEEKLY,
        expiry_date=expiry,
        strike_price=Decimal("50000"),
    )
    assert info.is_derivative
    assert info.is_option
    assert not info.is_perpetual
    assert info.strike_price == Decimal("50000")
    assert info.expiry_date == expiry


def test_option_validation() -> None:
    # Option requires strike price
    with pytest.raises(ValueError):
        MarketInfo(
            base="BTC",
            quote="USD",
            instrument_type=InstrumentType.CALL_OPTION,
            timeframe_type=InstrumentTimeframeType.WEEKLY,
            expiry_date=datetime(2024, 1, 1),
        )

    # Option requires expiry date
    with pytest.raises(ValueError):
        MarketInfo(
            base="BTC",
            quote="USD",
            instrument_type=InstrumentType.CALL_OPTION,
            timeframe_type=InstrumentTimeframeType.WEEKLY,
            strike_price=Decimal("50000"),
        )


def test_split_client_instrument_name() -> None:
    # Test spot
    info = MarketInfo.split_client_instrument_name("BTC-USD")
    assert info.base == "BTC"
    assert info.quote == "USD"
    assert info.instrument_type == InstrumentType.SPOT

    # Test perpetual
    info = MarketInfo.split_client_instrument_name("BTC-USD-PERPETUAL")
    assert info.instrument_type == InstrumentType.PERPETUAL

    # Test option
    info = MarketInfo.split_client_instrument_name(
        "BTC-USD-CALL_OPTION-1W-20240101-50000"
    )
    assert info.instrument_type == InstrumentType.CALL_OPTION
    assert info.timeframe_type == InstrumentTimeframeType.WEEKLY
    assert info.expiry_date == datetime(2024, 1, 1)
    assert info.strike_price == Decimal("50000")
