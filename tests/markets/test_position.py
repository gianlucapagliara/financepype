from decimal import Decimal

import pytest
from pydantic import ValidationError

from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.constants import s_decimal_0, s_decimal_inf
from financepype.markets.position import Position
from financepype.platforms.platform import Platform


@pytest.fixture
def platform() -> Platform:
    return Platform(identifier="binance")


@pytest.fixture
def long_contract(platform: Platform) -> DerivativeContract:
    return DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value="BTC-USDT-PERPETUAL"),
        side=DerivativeSide.LONG,
    )


@pytest.fixture
def short_contract(platform: Platform) -> DerivativeContract:
    return DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value="BTC-USDT-PERPETUAL"),
        side=DerivativeSide.SHORT,
    )


@pytest.fixture
def long_position(long_contract: DerivativeContract) -> Position:
    return Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("100"),
        liquidation_price=Decimal("45000"),
    )


@pytest.fixture
def short_position(short_contract: DerivativeContract) -> Position:
    return Position(
        asset=short_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("-100"),
        liquidation_price=Decimal("55000"),
    )


def test_position_initialization(long_contract: DerivativeContract) -> None:
    position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("45000"),
    )
    assert position.asset == long_contract
    assert position.amount == Decimal("0.1")
    assert position.leverage == Decimal("2")
    assert position.entry_price == Decimal("50000")
    assert position.margin == Decimal("1000")
    assert position.unrealized_pnl == Decimal("0")
    assert position.liquidation_price == Decimal("45000")


def test_position_validation(long_contract: DerivativeContract) -> None:
    # Test amount > 0
    with pytest.raises(ValidationError):
        Position(
            asset=long_contract,
            amount=Decimal("0"),
            leverage=Decimal("2"),
            entry_price=Decimal("50000"),
            entry_index_price=Decimal("50000"),
            margin=Decimal("1000"),
            unrealized_pnl=Decimal("0"),
            liquidation_price=Decimal("45000"),
        )

    # Test leverage > 0
    with pytest.raises(ValidationError):
        Position(
            asset=long_contract,
            amount=Decimal("0.1"),
            leverage=Decimal("0"),
            entry_price=Decimal("50000"),
            entry_index_price=Decimal("50000"),
            margin=Decimal("1000"),
            unrealized_pnl=Decimal("0"),
            liquidation_price=Decimal("45000"),
        )

    # Test entry_price > 0
    with pytest.raises(ValidationError):
        Position(
            asset=long_contract,
            amount=Decimal("0.1"),
            leverage=Decimal("2"),
            entry_price=Decimal("0"),
            entry_index_price=Decimal("50000"),
            margin=Decimal("1000"),
            unrealized_pnl=Decimal("0"),
            liquidation_price=Decimal("45000"),
        )

    # Test margin >= 0
    with pytest.raises(ValidationError):
        Position(
            asset=long_contract,
            amount=Decimal("0.1"),
            leverage=Decimal("2"),
            entry_price=Decimal("50000"),
            entry_index_price=Decimal("50000"),
            margin=Decimal("-1"),
            unrealized_pnl=Decimal("0"),
            liquidation_price=Decimal("45000"),
        )


def test_liquidation_price_validation(long_contract: DerivativeContract) -> None:
    # Test with negative liquidation price
    position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("-1"),
    )
    assert position.liquidation_price == s_decimal_0


def test_unrealized_percentage_pnl(long_position: Position) -> None:
    # 100 / 1000 * 100 = 10%
    assert long_position.unrealized_percentage_pnl == Decimal("10")


def test_position_value(long_position: Position) -> None:
    # 50000 * 0.1 = 5000
    assert long_position.value == Decimal("5000")


def test_position_side_properties(
    long_position: Position, short_position: Position
) -> None:
    # Test long position
    assert long_position.position_side == DerivativeSide.LONG
    assert long_position.is_long is True
    assert long_position.is_short is False

    # Test short position
    assert short_position.position_side == DerivativeSide.SHORT
    assert short_position.is_long is False
    assert short_position.is_short is True


def test_distance_from_liquidation(
    long_position: Position, short_position: Position
) -> None:
    # Long position: current_price - liquidation_price
    assert long_position.distance_from_liquidation(Decimal("48000")) == Decimal("3000")
    # Short position: liquidation_price - current_price
    assert short_position.distance_from_liquidation(Decimal("52000")) == Decimal("3000")


def test_percentage_from_liquidation(long_contract: DerivativeContract) -> None:
    # Test normal case
    position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("100"),
        liquidation_price=Decimal("45000"),
    )
    assert position.percentage_from_liquidation(Decimal("48000")) == Decimal(
        "3000"
    ) / Decimal("45000")

    # Test with zero liquidation price
    zero_liq_position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("100"),
        liquidation_price=s_decimal_0,
    )
    assert (
        zero_liq_position.percentage_from_liquidation(Decimal("48000")) == s_decimal_inf
    )


def test_margin_distance_from_liquidation(
    long_position: Position, short_position: Position
) -> None:
    # Long position: margin + unrealized_pnl = 1000 + 100 = 1100
    assert long_position.margin_distance_from_liquidation(Decimal("48000")) == Decimal(
        "1100"
    )
    # Short position: margin + unrealized_pnl = 1000 - 100 = 900
    assert short_position.margin_distance_from_liquidation(Decimal("52000")) == Decimal(
        "900"
    )


def test_margin_percentage_from_liquidation(long_position: Position) -> None:
    # margin_distance = 1100, margin = 1000
    # percentage = 1100 / 1000 = 1.1
    assert long_position.margin_percentage_from_liquidation(
        Decimal("48000")
    ) == Decimal("1.1")


def test_is_at_liquidation_risk(long_position: Position) -> None:
    # margin_percentage = 110%, default max_percentage = 95%
    assert not long_position.is_at_liquidation_risk(Decimal("48000"))

    # Test with custom max_percentage
    assert long_position.is_at_liquidation_risk(Decimal("48000"), Decimal("120"))


def test_negative_unrealized_pnl_percentage(short_contract: DerivativeContract) -> None:
    # Test position with negative unrealized PnL
    position = Position(
        asset=short_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("-500"),  # 50% loss
        liquidation_price=Decimal("55000"),
    )
    assert position.unrealized_percentage_pnl == Decimal("-50")


def test_margin_percentage_from_liquidation_with_negative_pnl(
    short_contract: DerivativeContract,
) -> None:
    # Test position with negative unrealized PnL near liquidation
    position = Position(
        asset=short_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("-900"),  # 90% loss
        liquidation_price=Decimal("55000"),
    )
    assert position.margin_percentage_from_liquidation(Decimal("54000")) == Decimal(
        "0.1"
    )


def test_distance_from_liquidation_at_liquidation_price(
    long_position: Position, short_position: Position
) -> None:
    # Test distance when price equals liquidation price
    assert long_position.distance_from_liquidation(Decimal("45000")) == Decimal("0")
    assert short_position.distance_from_liquidation(Decimal("55000")) == Decimal("0")


def test_distance_from_liquidation_beyond_liquidation(
    long_position: Position, short_position: Position
) -> None:
    # Test distance when price is beyond liquidation price
    assert long_position.distance_from_liquidation(Decimal("44000")) == Decimal("-1000")
    assert short_position.distance_from_liquidation(Decimal("56000")) == Decimal(
        "-1000"
    )


def test_high_leverage_position(long_contract: DerivativeContract) -> None:
    # Test position with high leverage (100x)
    position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("100"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("50"),  # 5000/100
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("49500"),  # Close to entry due to high leverage
    )

    # Small price movement should create significant PnL percentage
    # 1% price move = 100% PnL due to 100x leverage
    position.unrealized_pnl = Decimal("50")  # 100% of margin
    assert position.unrealized_percentage_pnl == Decimal("100")

    # Test liquidation risk with negative PnL
    position.unrealized_pnl = Decimal("-47.5")  # 95% loss
    assert position.margin_percentage_from_liquidation(Decimal("49600")) == Decimal(
        "0.05"
    )  # 5% margin left
    assert position.is_at_liquidation_risk(
        Decimal("49600")
    )  # Should be at risk with only 5% margin left


def test_zero_margin_validation(long_contract: DerivativeContract) -> None:
    # Test that zero margin is allowed (for example, in cross-margin mode)
    position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("45000"),
    )
    assert position.margin == Decimal("0")


def test_unrealized_pnl_with_zero_margin(long_contract: DerivativeContract) -> None:
    # Test PnL percentage calculation with zero margin
    position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("0"),
        unrealized_pnl=Decimal("100"),
        liquidation_price=Decimal("45000"),
    )
    # Should handle division by zero gracefully
    with pytest.raises(ZeroDivisionError):
        _ = position.unrealized_percentage_pnl


def test_margin_percentage_with_zero_margin(long_contract: DerivativeContract) -> None:
    # Test margin percentage calculation with zero margin
    position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("0"),
        unrealized_pnl=Decimal("100"),
        liquidation_price=Decimal("45000"),
    )
    # Should handle division by zero gracefully
    with pytest.raises(ZeroDivisionError):
        _ = position.margin_percentage_from_liquidation(Decimal("48000"))


def test_extreme_values(long_contract: DerivativeContract) -> None:
    # Test position with extreme values
    position = Position(
        asset=long_contract,
        amount=Decimal("999999.99999"),  # Very large amount
        leverage=Decimal("1000"),  # Very high leverage
        entry_price=Decimal("999999.99999"),  # Very high price
        entry_index_price=Decimal("999999.99999"),
        margin=Decimal("0.00001"),  # Very small margin
        unrealized_pnl=Decimal("-0.00001"),  # Very small negative PnL
        liquidation_price=Decimal("999998.99999"),  # Very close to entry price
    )

    # Test calculations with extreme values
    assert position.value == Decimal("999999.99999") * Decimal("999999.99999")
    assert position.unrealized_percentage_pnl == Decimal("-100")
    assert position.is_at_liquidation_risk(Decimal("999999"))


def test_liquidation_risk_edge_cases(long_contract: DerivativeContract) -> None:
    position = Position(
        asset=long_contract,
        amount=Decimal("0.1"),
        leverage=Decimal("2"),
        entry_price=Decimal("50000"),
        entry_index_price=Decimal("50000"),
        margin=Decimal("1000"),
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("45000"),
    )

    # Test exactly at max_percentage
    max_percentage = Decimal("95")
    position.unrealized_pnl = Decimal(
        "-50"
    )  # Set PnL to get exactly 95% margin remaining
    assert position.margin_percentage_from_liquidation(Decimal("48000")) == Decimal(
        "0.95"
    )
    assert position.is_at_liquidation_risk(Decimal("48000"), max_percentage)

    # Test slightly above max_percentage
    position.unrealized_pnl = Decimal("-49")  # Slightly better PnL
    assert not position.is_at_liquidation_risk(Decimal("48000"), max_percentage)

    # Test slightly below max_percentage
    position.unrealized_pnl = Decimal("-51")  # Slightly worse PnL
    assert position.is_at_liquidation_risk(Decimal("48000"), max_percentage)


def test_model_validation(long_contract: DerivativeContract) -> None:
    # Test model-level validation
    with pytest.raises(ValidationError) as exc_info:
        Position(
            asset=long_contract,
            amount=Decimal("-0.1"),  # Invalid: negative amount
            leverage=Decimal("-2"),  # Invalid: negative leverage
            entry_price=Decimal("-50000"),  # Invalid: negative entry price
            entry_index_price=Decimal("50000"),
            margin=Decimal("-1000"),  # Invalid: negative margin
            unrealized_pnl=Decimal("0"),
            liquidation_price=Decimal("-45000"),  # Will be converted to 0
        )

    errors = exc_info.value.errors()
    error_fields = {error["loc"][0] for error in errors}
    assert error_fields == {
        "amount",
        "leverage",
        "entry_price",
        "margin",
    }  # All invalid fields should be caught
