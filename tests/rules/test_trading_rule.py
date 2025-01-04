from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from financepype.markets.trading_pair import TradingPair
from financepype.rules.trading_rule import DerivativeTradingRule, TradingRule


@pytest.fixture
def trading_pair() -> TradingPair:
    return TradingPair(name="BTC-USDT")


@pytest.fixture
def basic_rule(trading_pair: TradingPair) -> TradingRule:
    return TradingRule(
        trading_pair=trading_pair,
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100"),
        min_price_increment=Decimal("0.01"),
        min_price_significance=2,
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
        max_notional_size=Decimal("1000000"),
    )


@pytest.fixture
def derivative_rule(trading_pair: TradingPair) -> DerivativeTradingRule:
    return DerivativeTradingRule(
        trading_pair=trading_pair,
        underlying="BTC",
        strike_price=Decimal("50000"),
        start_timestamp=datetime.now().timestamp(),
        expiry_timestamp=datetime.now().timestamp() + 86400,  # 1 day from now
        index_symbol="BTC/USD",
    )


def test_trading_rule_initialization(
    basic_rule: TradingRule, trading_pair: TradingPair
) -> None:
    """Test basic initialization of TradingRule."""
    assert basic_rule.trading_pair == trading_pair
    assert basic_rule.min_order_size == Decimal("0.001")
    assert basic_rule.max_order_size == Decimal("100")
    assert basic_rule.min_price_increment == Decimal("0.01")
    assert basic_rule.min_price_significance == 2
    assert basic_rule.min_base_amount_increment == Decimal("0.001")
    assert basic_rule.min_quote_amount_increment == Decimal("0.01")
    assert basic_rule.min_notional_size == Decimal("10")
    assert basic_rule.max_notional_size == Decimal("1000000")
    assert basic_rule.supports_limit_orders is True
    assert basic_rule.supports_market_orders is True
    assert basic_rule.is_live is True


def test_trading_rule_collateral_tokens(basic_rule: TradingRule) -> None:
    """Test collateral token assignment."""
    assert basic_rule.buy_order_collateral_token == "USDT"
    assert basic_rule.sell_order_collateral_token == "BTC"


def test_trading_rule_custom_collateral_tokens(trading_pair: TradingPair) -> None:
    """Test custom collateral token assignment."""
    rule = TradingRule(
        trading_pair=trading_pair,
        buy_order_collateral_token="DAI",
        sell_order_collateral_token="WBTC",
    )
    assert rule.buy_order_collateral_token == "DAI"
    assert rule.sell_order_collateral_token == "WBTC"


def test_trading_rule_properties(basic_rule: TradingRule) -> None:
    """Test TradingRule properties."""
    assert basic_rule.active is True
    assert basic_rule.started is True
    assert basic_rule.expired is False


def test_trading_rule_timestamp_methods(basic_rule: TradingRule) -> None:
    """Test TradingRule timestamp-based methods."""
    current_time = datetime.now().timestamp()
    assert basic_rule.is_active(current_time) is True
    assert basic_rule.is_started(current_time) is True
    assert basic_rule.is_expired(current_time) is False


def test_derivative_rule_initialization(derivative_rule: DerivativeTradingRule) -> None:
    """Test initialization of DerivativeTradingRule."""
    assert derivative_rule.underlying == "BTC"
    assert derivative_rule.strike_price == Decimal("50000")
    assert derivative_rule.index_symbol == "BTC/USD"
    assert derivative_rule.perpetual is False


def test_derivative_rule_perpetual(trading_pair: TradingPair) -> None:
    """Test perpetual derivative rule."""
    perpetual = DerivativeTradingRule(
        trading_pair=trading_pair,
        underlying="BTC",
        index_symbol="BTC/USD",
        expiry_timestamp=-1,
    )
    assert perpetual.perpetual is True
    assert perpetual.is_expired() is False


def test_derivative_rule_expiry(derivative_rule: DerivativeTradingRule) -> None:
    """Test derivative rule expiry."""
    # Test before expiry
    current_time = datetime.now().timestamp()
    assert derivative_rule.is_expired(current_time) is False

    # Test after expiry
    future_time = current_time + 172800  # 2 days from now
    assert derivative_rule.is_expired(future_time) is True


def test_derivative_rule_start_time(trading_pair: TradingPair) -> None:
    """Test derivative rule start time."""
    future_start = datetime.now() + timedelta(days=1)
    rule = DerivativeTradingRule(
        trading_pair=trading_pair,
        underlying="BTC",
        start_timestamp=future_start.timestamp(),
        expiry_timestamp=future_start.timestamp() + 86400,
    )

    # Test before start
    current_time = datetime.now().timestamp()
    assert rule.is_started(current_time) is False
    assert rule.is_active(current_time) is False

    # Test after start but before expiry
    during_time = future_start.timestamp() + 3600  # 1 hour after start
    assert rule.is_started(during_time) is True
    assert rule.is_active(during_time) is True


def test_derivative_rule_active_states(derivative_rule: DerivativeTradingRule) -> None:
    """Test various active states of derivative rule."""
    current_time = datetime.now().timestamp()

    # Active during valid period
    assert derivative_rule.is_active(current_time) is True

    # Inactive before start
    derivative_rule.start_timestamp = current_time + 86400  # 1 day in future
    assert derivative_rule.is_active(current_time) is False

    # Inactive after expiry
    derivative_rule.start_timestamp = current_time - 86400  # 1 day ago
    derivative_rule.expiry_timestamp = current_time - 3600  # 1 hour ago
    assert derivative_rule.is_active(current_time) is False


def test_trading_rule_serialization(basic_rule: TradingRule) -> None:
    """Test serialization of decimal fields."""
    model_dump = basic_rule.model_dump()
    assert isinstance(model_dump["min_order_size"], str)
    assert isinstance(model_dump["max_order_size"], str)
    assert isinstance(model_dump["min_price_increment"], str)
    assert isinstance(model_dump["min_base_amount_increment"], str)
    assert isinstance(model_dump["min_quote_amount_increment"], str)
    assert isinstance(model_dump["min_notional_size"], str)
    assert isinstance(model_dump["max_notional_size"], str)


def test_derivative_rule_serialization(derivative_rule: DerivativeTradingRule) -> None:
    """Test serialization of strike price in derivative rule."""
    model_dump = derivative_rule.model_dump()
    assert isinstance(model_dump["strike_price"], str)

    # Test None value
    derivative_rule.strike_price = None
    model_dump = derivative_rule.model_dump()
    assert model_dump["strike_price"] is None
