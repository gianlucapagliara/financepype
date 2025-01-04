import pytest

from financepype.markets.market import InstrumentType
from financepype.markets.trading_pair import TradingPair


def test_trading_pair_creation() -> None:
    pair = TradingPair(name="BTC-USD")
    assert pair.name == "BTC-USD"
    assert pair.base == "BTC"
    assert pair.quote == "USD"
    assert pair.instrument_type == InstrumentType.SPOT


def test_trading_pair_validation() -> None:
    with pytest.raises(ValueError):
        TradingPair(name="invalid-format-instrument")


def test_trading_pair_singleton() -> None:
    pair1 = TradingPair(name="BTC-USD")
    pair2 = TradingPair(name="BTC-USD")
    assert pair1 is pair2  # Same instance


def test_derivative_trading_pair() -> None:
    pair = TradingPair(name="BTC-USD-PERPETUAL")
    assert pair.name == "BTC-USD-PERPETUAL"
    assert pair.base == "BTC"
    assert pair.quote == "USD"
    assert pair.instrument_type == InstrumentType.PERPETUAL
    assert pair.instrument_info.is_derivative


def test_option_trading_pair() -> None:
    pair = TradingPair(name="BTC-USD-CALL_OPTION-1W-20240101-50000")
    assert pair.base == "BTC"
    assert pair.quote == "USD"
    assert pair.instrument_type == InstrumentType.CALL_OPTION
    assert pair.instrument_info.is_option
