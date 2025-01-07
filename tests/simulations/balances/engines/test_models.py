from decimal import Decimal

import pytest
from pydantic import ValidationError

from financepype.assets.spot import SpotAsset
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import OrderType, PositionAction, TradeType
from financepype.platforms.platform import Platform
from financepype.rules.trading_rule import TradingRule
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    CashflowReason,
    CashflowType,
    InvolvementType,
    OrderDetails,
)


@pytest.fixture
def trading_rule(platform: Platform) -> TradingRule:
    return TradingRule(
        trading_pair=TradingPair(name="BTC-USD"),
        min_order_size=Decimal("0.0001"),
        min_price_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
    )


@pytest.fixture
def order_details(
    platform: Platform, btc_asset: SpotAsset, trading_rule: TradingRule
) -> OrderDetails:
    return OrderDetails(
        platform=platform,
        trading_pair=TradingPair(name="BTC-USD"),
        trading_rule=trading_rule,
        trade_type=TradeType.BUY,
        order_type=OrderType.MARKET,
        amount=Decimal("1.0"),
        price=Decimal("50000"),
        leverage=1,
        position_action=PositionAction.OPEN,
        index_price=Decimal("50000"),
        fee=OperationFee(
            asset=btc_asset,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


def test_asset_cashflow_creation(btc_asset: SpotAsset) -> None:
    cashflow = AssetCashflow(
        asset=btc_asset,
        involvement_type=InvolvementType.OPENING,
        cashflow_type=CashflowType.OUTFLOW,
        reason=CashflowReason.OPERATION,
        amount=Decimal("1.0"),
    )
    assert cashflow.asset == btc_asset
    assert cashflow.amount == Decimal("1.0")
    assert cashflow.involvement_type == InvolvementType.OPENING
    assert cashflow.cashflow_type == CashflowType.OUTFLOW
    assert cashflow.reason == CashflowReason.OPERATION


def test_order_details_validation(
    platform: Platform, btc_asset: SpotAsset, trading_rule: TradingRule
) -> None:
    # Test invalid amount
    with pytest.raises(ValidationError):
        OrderDetails(
            platform=platform,
            trading_pair=TradingPair(name="BTC-USD"),
            trading_rule=trading_rule,
            trade_type=TradeType.BUY,
            order_type=OrderType.MARKET,
            amount=Decimal("-1.0"),  # Invalid negative amount
            price=Decimal("50000"),
            leverage=1,
            position_action=PositionAction.OPEN,
            index_price=Decimal("50000"),
            fee=OperationFee(
                asset=btc_asset,
                amount=Decimal("0.1"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )


def test_operation_fee_validation(btc_asset: SpotAsset) -> None:
    # Test invalid percentage
    with pytest.raises(ValidationError):
        OperationFee(
            asset=btc_asset,
            amount=Decimal("101"),  # Invalid percentage > 100
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        )

    # Test negative fee
    with pytest.raises(ValidationError):
        OperationFee(
            asset=btc_asset,
            amount=Decimal("-0.1"),  # Invalid negative fee
            fee_type=FeeType.ABSOLUTE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        )
