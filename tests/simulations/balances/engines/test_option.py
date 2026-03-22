from decimal import Decimal

import pytest

from financepype.assets.asset import Asset
from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.assets.factory import AssetFactory
from financepype.markets.position import Position
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import OrderType, PositionAction, TradeType
from financepype.platforms.platform import Platform
from financepype.rules.trading_rule import TradingRule
from financepype.simulations.balances.engines.models import (
    CashflowReason,
    CashflowType,
    InvolvementType,
    OrderDetails,
)
from financepype.simulations.balances.engines.option import (
    InverseOptionBalanceEngine,
    OptionBalanceEngine,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def platform() -> Platform:
    return Platform(identifier="test")


@pytest.fixture
def call_trading_pair() -> TradingPair:
    return TradingPair(name="BTC-USDT-CALL_OPTION-1D-20240630-50000")


@pytest.fixture
def put_trading_pair() -> TradingPair:
    return TradingPair(name="BTC-USDT-PUT_OPTION-1D-20240630-50000")


@pytest.fixture
def inverse_call_trading_pair() -> TradingPair:
    return TradingPair(name="BTC-USD-INVERSE_CALL_OPTION-1D-20240630-50000")


@pytest.fixture
def inverse_put_trading_pair() -> TradingPair:
    return TradingPair(name="BTC-USD-INVERSE_PUT_OPTION-1D-20240630-50000")


@pytest.fixture
def call_trading_rule(call_trading_pair: TradingPair) -> TradingRule:
    return TradingRule(
        trading_pair=call_trading_pair,
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100"),
        min_price_increment=Decimal("0.01"),
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
        max_notional_size=Decimal("1000000"),
        buy_order_collateral_token="USDT",
        sell_order_collateral_token="USDT",
    )


@pytest.fixture
def put_trading_rule(put_trading_pair: TradingPair) -> TradingRule:
    return TradingRule(
        trading_pair=put_trading_pair,
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100"),
        min_price_increment=Decimal("0.01"),
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
        max_notional_size=Decimal("1000000"),
        buy_order_collateral_token="USDT",
        sell_order_collateral_token="USDT",
    )


@pytest.fixture
def inverse_call_trading_rule(inverse_call_trading_pair: TradingPair) -> TradingRule:
    return TradingRule(
        trading_pair=inverse_call_trading_pair,
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100000"),
        min_price_increment=Decimal("0.01"),
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
        max_notional_size=Decimal("10000000"),
        buy_order_collateral_token="BTC",
        sell_order_collateral_token="BTC",
    )


@pytest.fixture
def inverse_put_trading_rule(inverse_put_trading_pair: TradingPair) -> TradingRule:
    return TradingRule(
        trading_pair=inverse_put_trading_pair,
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100000"),
        min_price_increment=Decimal("0.01"),
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
        min_notional_size=Decimal("10"),
        max_notional_size=Decimal("10000000"),
        buy_order_collateral_token="BTC",
        sell_order_collateral_token="BTC",
    )


@pytest.fixture
def quote_asset(platform: Platform, call_trading_pair: TradingPair) -> Asset:
    return AssetFactory.get_asset(platform, call_trading_pair.quote)


@pytest.fixture
def base_asset(platform: Platform, call_trading_pair: TradingPair) -> Asset:
    return AssetFactory.get_asset(platform, call_trading_pair.base)


def _make_position(
    platform: Platform,
    trading_pair: TradingPair,
    side: DerivativeSide,
    amount: Decimal = Decimal("1"),
    entry_price: Decimal = Decimal("1000"),
    entry_index_price: Decimal = Decimal("50000"),
    margin: Decimal = Decimal("0"),
) -> Position:
    contract = DerivativeContract(
        platform=platform,
        identifier=AssetIdentifier(value=trading_pair.name),
        side=side,
    )
    return Position(
        asset=contract,
        amount=amount,
        leverage=Decimal("1"),
        entry_price=entry_price,
        entry_index_price=entry_index_price,
        margin=margin,
        unrealized_pnl=Decimal("0"),
        liquidation_price=Decimal("0"),
    )


# --- Regular option order fixtures ---


@pytest.fixture
def open_long_call(
    platform: Platform,
    call_trading_pair: TradingPair,
    call_trading_rule: TradingRule,
    quote_asset: Asset,
) -> OrderDetails:
    """Open long call: BUY + OPEN."""
    return OrderDetails(
        platform=platform,
        trading_pair=call_trading_pair,
        trading_rule=call_trading_rule,
        amount=Decimal("1"),
        price=Decimal("1000"),
        leverage=1,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        index_price=Decimal("50000"),
        fee=OperationFee(
            asset=quote_asset,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


@pytest.fixture
def open_short_call(
    platform: Platform,
    call_trading_pair: TradingPair,
    call_trading_rule: TradingRule,
    quote_asset: Asset,
) -> OrderDetails:
    """Open short call: SELL + OPEN."""
    return OrderDetails(
        platform=platform,
        trading_pair=call_trading_pair,
        trading_rule=call_trading_rule,
        amount=Decimal("1"),
        price=Decimal("1000"),
        leverage=1,
        trade_type=TradeType.SELL,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        index_price=Decimal("50000"),
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


@pytest.fixture
def close_long_call(
    platform: Platform,
    call_trading_pair: TradingPair,
    call_trading_rule: TradingRule,
    quote_asset: Asset,
) -> OrderDetails:
    """Close long call: SELL + CLOSE (deliver LONG position)."""
    position = _make_position(
        platform, call_trading_pair, DerivativeSide.LONG, amount=Decimal("1")
    )
    return OrderDetails(
        platform=platform,
        trading_pair=call_trading_pair,
        trading_rule=call_trading_rule,
        amount=Decimal("1"),
        price=Decimal("1200"),
        leverage=1,
        trade_type=TradeType.SELL,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.CLOSE,
        index_price=Decimal("52000"),
        current_position=position,
        fee=OperationFee(
            asset=quote_asset,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


@pytest.fixture
def close_short_call(
    platform: Platform,
    call_trading_pair: TradingPair,
    call_trading_rule: TradingRule,
    quote_asset: Asset,
) -> OrderDetails:
    """Close short call: BUY + CLOSE (deliver SHORT position)."""
    position = _make_position(
        platform, call_trading_pair, DerivativeSide.SHORT, amount=Decimal("1")
    )
    return OrderDetails(
        platform=platform,
        trading_pair=call_trading_pair,
        trading_rule=call_trading_rule,
        amount=Decimal("1"),
        price=Decimal("800"),
        leverage=1,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.CLOSE,
        index_price=Decimal("48000"),
        current_position=position,
        fee=OperationFee(
            asset=quote_asset,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


@pytest.fixture
def flip_short_to_long_call(
    platform: Platform,
    call_trading_pair: TradingPair,
    call_trading_rule: TradingRule,
    quote_asset: Asset,
) -> OrderDetails:
    """Flip from short to long: BUY + FLIP (amount > current position)."""
    position = _make_position(
        platform, call_trading_pair, DerivativeSide.SHORT, amount=Decimal("1")
    )
    return OrderDetails(
        platform=platform,
        trading_pair=call_trading_pair,
        trading_rule=call_trading_rule,
        amount=Decimal("2"),
        price=Decimal("1000"),
        leverage=1,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.FLIP,
        index_price=Decimal("50000"),
        current_position=position,
        fee=OperationFee(
            asset=quote_asset,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


# --- Inverse option order fixtures ---


@pytest.fixture
def inverse_open_long_call(
    platform: Platform,
    inverse_call_trading_pair: TradingPair,
    inverse_call_trading_rule: TradingRule,
) -> OrderDetails:
    """Open long inverse call: BUY + OPEN."""
    return OrderDetails(
        platform=platform,
        trading_pair=inverse_call_trading_pair,
        trading_rule=inverse_call_trading_rule,
        amount=Decimal("50000"),
        price=Decimal("0.02"),
        leverage=1,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        index_price=Decimal("50000"),
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


@pytest.fixture
def inverse_open_short_call(
    platform: Platform,
    inverse_call_trading_pair: TradingPair,
    inverse_call_trading_rule: TradingRule,
) -> OrderDetails:
    """Open short inverse call: SELL + OPEN."""
    return OrderDetails(
        platform=platform,
        trading_pair=inverse_call_trading_pair,
        trading_rule=inverse_call_trading_rule,
        amount=Decimal("50000"),
        price=Decimal("0.02"),
        leverage=1,
        trade_type=TradeType.SELL,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        index_price=Decimal("50000"),
        fee=OperationFee(
            asset=None,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


# --- Put option fixtures ---


@pytest.fixture
def open_long_put(
    platform: Platform,
    put_trading_pair: TradingPair,
    put_trading_rule: TradingRule,
    quote_asset: Asset,
) -> OrderDetails:
    """Open long put: BUY + OPEN."""
    return OrderDetails(
        platform=platform,
        trading_pair=put_trading_pair,
        trading_rule=put_trading_rule,
        amount=Decimal("1"),
        price=Decimal("500"),
        leverage=1,
        trade_type=TradeType.BUY,
        order_type=OrderType.LIMIT,
        position_action=PositionAction.OPEN,
        index_price=Decimal("50000"),
        fee=OperationFee(
            asset=quote_asset,
            amount=Decimal("0.1"),
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        ),
    )


# =============================================================================
# Regular Option Engine: Premium & Fee Calculations
# =============================================================================


class TestRegularOptionPremium:
    def test_premium_calculation(self, open_long_call: OrderDetails) -> None:
        """Premium = amount * price = 1 * 1000 = 1000."""
        assert OptionBalanceEngine._calculate_premium(open_long_call) == Decimal("1000")

    def test_premium_different_values(
        self,
        platform: Platform,
        call_trading_pair: TradingPair,
        call_trading_rule: TradingRule,
        quote_asset: Asset,
    ) -> None:
        """Premium = 5 * 200 = 1000."""
        order = OrderDetails(
            platform=platform,
            trading_pair=call_trading_pair,
            trading_rule=call_trading_rule,
            amount=Decimal("5"),
            price=Decimal("200"),
            leverage=1,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            position_action=PositionAction.OPEN,
            index_price=Decimal("50000"),
            fee=OperationFee(
                asset=quote_asset,
                amount=Decimal("0"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )
        assert OptionBalanceEngine._calculate_premium(order) == Decimal("1000")


class TestRegularOptionFee:
    def test_percentage_fee(self, open_long_call: OrderDetails) -> None:
        """0.1% of premium (1000) = 1 USDT."""
        fee = OptionBalanceEngine._calculate_fee_amount(open_long_call)
        assert fee == Decimal("1")

    def test_absolute_fee(
        self, open_long_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """Absolute fee of 10 USDT."""
        order = open_long_call.model_copy(
            update={
                "fee": OperationFee(
                    asset=quote_asset,
                    amount=Decimal("10"),
                    fee_type=FeeType.ABSOLUTE,
                    impact_type=FeeImpactType.ADDED_TO_COSTS,
                )
            }
        )
        fee = OptionBalanceEngine._calculate_fee_amount(order)
        assert fee == Decimal("10")

    def test_fee_wrong_asset_raises(
        self, open_long_call: OrderDetails, base_asset: Asset
    ) -> None:
        """Fee in base currency should raise for regular options."""
        order = open_long_call.model_copy(
            update={
                "fee": OperationFee(
                    asset=base_asset,
                    amount=Decimal("0.1"),
                    fee_type=FeeType.PERCENTAGE,
                    impact_type=FeeImpactType.ADDED_TO_COSTS,
                )
            }
        )
        with pytest.raises(NotImplementedError):
            OptionBalanceEngine._calculate_fee_amount(order)

    def test_absolute_fee_requires_asset(self, open_long_call: OrderDetails) -> None:
        """Absolute fee without asset should raise."""
        order = open_long_call.model_copy(
            update={
                "fee": OperationFee(
                    asset=None,
                    amount=Decimal("10"),
                    fee_type=FeeType.ABSOLUTE,
                    impact_type=FeeImpactType.ADDED_TO_COSTS,
                )
            }
        )
        with pytest.raises(ValueError, match="Fee asset is required"):
            OptionBalanceEngine._calculate_fee_amount(order)


# =============================================================================
# Regular Option Engine: Settlement Calculations
# =============================================================================


class TestRegularOptionSettlement:
    def test_call_itm_settlement(self, open_long_call: OrderDetails) -> None:
        """Call ITM: max(0, spot - strike) * size.
        spot=1000, strike=50000 → OTM → 0.
        """
        # With price=1000 and strike=50000, this call is OTM
        assert OptionBalanceEngine._calculate_settlement(open_long_call) == Decimal("0")

    def test_call_itm_settlement_positive(
        self,
        platform: Platform,
        call_trading_pair: TradingPair,
        call_trading_rule: TradingRule,
        quote_asset: Asset,
    ) -> None:
        """Call ITM: max(0, 55000 - 50000) * 1 = 5000."""
        order = OrderDetails(
            platform=platform,
            trading_pair=call_trading_pair,
            trading_rule=call_trading_rule,
            amount=Decimal("1"),
            price=Decimal("55000"),
            leverage=1,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            position_action=PositionAction.OPEN,
            index_price=Decimal("55000"),
            fee=OperationFee(
                asset=quote_asset,
                amount=Decimal("0"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )
        assert OptionBalanceEngine._calculate_settlement(order) == Decimal("5000")

    def test_put_itm_settlement(
        self,
        platform: Platform,
        put_trading_pair: TradingPair,
        put_trading_rule: TradingRule,
        quote_asset: Asset,
    ) -> None:
        """Put ITM: max(0, 50000 - 45000) * 1 = 5000."""
        order = OrderDetails(
            platform=platform,
            trading_pair=put_trading_pair,
            trading_rule=put_trading_rule,
            amount=Decimal("1"),
            price=Decimal("45000"),
            leverage=1,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            position_action=PositionAction.OPEN,
            index_price=Decimal("45000"),
            fee=OperationFee(
                asset=quote_asset,
                amount=Decimal("0"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )
        assert OptionBalanceEngine._calculate_settlement(order) == Decimal("5000")

    def test_put_otm_settlement(
        self,
        platform: Platform,
        put_trading_pair: TradingPair,
        put_trading_rule: TradingRule,
        quote_asset: Asset,
    ) -> None:
        """Put OTM: max(0, 50000 - 55000) * 1 = 0."""
        order = OrderDetails(
            platform=platform,
            trading_pair=put_trading_pair,
            trading_rule=put_trading_rule,
            amount=Decimal("1"),
            price=Decimal("55000"),
            leverage=1,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            position_action=PositionAction.OPEN,
            index_price=Decimal("55000"),
            fee=OperationFee(
                asset=quote_asset,
                amount=Decimal("0"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )
        assert OptionBalanceEngine._calculate_settlement(order) == Decimal("0")


# =============================================================================
# Regular Option Engine: get_outflow_asset
# =============================================================================


class TestRegularOptionOutflowAsset:
    def test_buy_outflow_asset(
        self, open_long_call: OrderDetails, quote_asset: Asset
    ) -> None:
        assert OptionBalanceEngine._get_outflow_asset(open_long_call) == quote_asset

    def test_sell_outflow_asset(
        self, open_short_call: OrderDetails, quote_asset: Asset
    ) -> None:
        assert OptionBalanceEngine._get_outflow_asset(open_short_call) == quote_asset


# =============================================================================
# Regular Option Engine: get_involved_assets
# =============================================================================


class TestRegularOptionInvolvedAssets:
    def test_open_long(self, open_long_call: OrderDetails, quote_asset: Asset) -> None:
        """OPEN BUY: collateral outflow, position inflow, 2 fees."""
        assets = OptionBalanceEngine.get_involved_assets(open_long_call)
        assert len(assets) == 4

        # Premium outflow
        assert assets[0].asset == quote_asset
        assert assets[0].involvement_type == InvolvementType.OPENING
        assert assets[0].cashflow_type == CashflowType.OUTFLOW
        assert assets[0].reason == CashflowReason.OPERATION

        # Position inflow
        position_asset = AssetFactory.get_asset(
            open_long_call.platform,
            open_long_call.trading_pair.name,
            side=DerivativeSide.LONG,
        )
        assert assets[1].asset == position_asset
        assert assets[1].involvement_type == InvolvementType.CLOSING
        assert assets[1].cashflow_type == CashflowType.INFLOW
        assert assets[1].reason == CashflowReason.OPERATION

        # Opening fee
        assert assets[2].asset == quote_asset
        assert assets[2].reason == CashflowReason.FEE
        assert assets[2].involvement_type == InvolvementType.OPENING
        assert assets[2].cashflow_type == CashflowType.OUTFLOW

        # Closing fee
        assert assets[3].asset == quote_asset
        assert assets[3].reason == CashflowReason.FEE
        assert assets[3].involvement_type == InvolvementType.CLOSING
        assert assets[3].cashflow_type == CashflowType.OUTFLOW

    def test_open_short(
        self, open_short_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """OPEN SELL: margin outflow, premium inflow, position inflow, 2 fees."""
        assets = OptionBalanceEngine.get_involved_assets(open_short_call)
        assert len(assets) == 5

        # Margin outflow
        assert assets[0].asset == quote_asset
        assert assets[0].involvement_type == InvolvementType.OPENING
        assert assets[0].cashflow_type == CashflowType.OUTFLOW
        assert assets[0].reason == CashflowReason.MARGIN

        # Premium receipt (collateral inflow)
        assert assets[1].asset == quote_asset
        assert assets[1].involvement_type == InvolvementType.CLOSING
        assert assets[1].cashflow_type == CashflowType.INFLOW
        assert assets[1].reason == CashflowReason.OPERATION

        # Position inflow
        position_asset = AssetFactory.get_asset(
            open_short_call.platform,
            open_short_call.trading_pair.name,
            side=DerivativeSide.SHORT,
        )
        assert assets[2].asset == position_asset
        assert assets[2].involvement_type == InvolvementType.CLOSING
        assert assets[2].cashflow_type == CashflowType.INFLOW
        assert assets[2].reason == CashflowReason.OPERATION

        # Fees
        assert assets[3].reason == CashflowReason.FEE
        assert assets[4].reason == CashflowReason.FEE

    def test_close_long(
        self, close_long_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """CLOSE SELL: position outflow, premium inflow, 2 fees."""
        assets = OptionBalanceEngine.get_involved_assets(close_long_call)
        assert len(assets) == 4

        # Position outflow (deliver LONG position)
        position_asset = AssetFactory.get_asset(
            close_long_call.platform,
            close_long_call.trading_pair.name,
            side=DerivativeSide.LONG,
        )
        assert assets[0].asset == position_asset
        assert assets[0].involvement_type == InvolvementType.OPENING
        assert assets[0].cashflow_type == CashflowType.OUTFLOW
        assert assets[0].reason == CashflowReason.OPERATION

        # Premium receipt
        assert assets[1].asset == quote_asset
        assert assets[1].involvement_type == InvolvementType.CLOSING
        assert assets[1].cashflow_type == CashflowType.INFLOW
        assert assets[1].reason == CashflowReason.OPERATION

        # Fees
        assert assets[2].reason == CashflowReason.FEE
        assert assets[3].reason == CashflowReason.FEE

    def test_close_short(
        self, close_short_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """CLOSE BUY: position outflow, margin inflow, PnL inflow, 2 fees."""
        assets = OptionBalanceEngine.get_involved_assets(close_short_call)
        assert len(assets) == 5

        # Position outflow (deliver SHORT position)
        position_asset = AssetFactory.get_asset(
            close_short_call.platform,
            close_short_call.trading_pair.name,
            side=DerivativeSide.SHORT,
        )
        assert assets[0].asset == position_asset
        assert assets[0].involvement_type == InvolvementType.OPENING
        assert assets[0].cashflow_type == CashflowType.OUTFLOW
        assert assets[0].reason == CashflowReason.OPERATION

        # Margin return
        assert assets[1].asset == quote_asset
        assert assets[1].involvement_type == InvolvementType.CLOSING
        assert assets[1].cashflow_type == CashflowType.INFLOW
        assert assets[1].reason == CashflowReason.MARGIN

        # PnL
        assert assets[2].asset == quote_asset
        assert assets[2].involvement_type == InvolvementType.CLOSING
        assert assets[2].cashflow_type == CashflowType.INFLOW
        assert assets[2].reason == CashflowReason.PNL

        # Fees
        assert assets[3].reason == CashflowReason.FEE
        assert assets[4].reason == CashflowReason.FEE

    def test_flip_short_to_long(
        self, flip_short_to_long_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """FLIP splits into CLOSE(amount=1) + OPEN(amount=1)."""
        assets = OptionBalanceEngine.get_involved_assets(flip_short_to_long_call)
        # CLOSE BUY (5 items) + OPEN BUY (4 items) = 9
        assert len(assets) == 9


# =============================================================================
# Regular Option Engine: Opening Outflows
# =============================================================================


class TestRegularOptionOpeningOutflows:
    def test_open_long(self, open_long_call: OrderDetails, quote_asset: Asset) -> None:
        """Premium + fee."""
        outflows = OptionBalanceEngine.get_opening_outflows(open_long_call)
        assert len(outflows) == 2

        # Premium
        assert outflows[0].asset == quote_asset
        assert outflows[0].reason == CashflowReason.OPERATION
        assert outflows[0].amount == Decimal("1000")

        # Fee: 0.1% of 1000 = 1
        assert outflows[1].asset == quote_asset
        assert outflows[1].reason == CashflowReason.FEE
        assert outflows[1].amount == Decimal("1")

    def test_open_short(
        self, open_short_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """Margin + fee."""
        outflows = OptionBalanceEngine.get_opening_outflows(open_short_call)
        assert len(outflows) == 2

        # Margin (returns NaN since _calculate_margin is a stub)
        assert outflows[0].asset == quote_asset
        assert outflows[0].reason == CashflowReason.MARGIN
        assert outflows[0].amount.is_nan()

        # Fee
        assert outflows[1].reason == CashflowReason.FEE
        assert outflows[1].amount == Decimal("1")

    def test_close_long(self, close_long_call: OrderDetails) -> None:
        """Deliver position asset."""
        outflows = OptionBalanceEngine.get_opening_outflows(close_long_call)
        assert len(outflows) == 1

        position_asset = AssetFactory.get_asset(
            close_long_call.platform,
            close_long_call.trading_pair.name,
            side=DerivativeSide.LONG,
        )
        assert outflows[0].asset == position_asset
        assert outflows[0].reason == CashflowReason.OPERATION
        assert outflows[0].amount == Decimal("1")

    def test_close_short(self, close_short_call: OrderDetails) -> None:
        """Deliver position asset."""
        outflows = OptionBalanceEngine.get_opening_outflows(close_short_call)
        assert len(outflows) == 1

        position_asset = AssetFactory.get_asset(
            close_short_call.platform,
            close_short_call.trading_pair.name,
            side=DerivativeSide.SHORT,
        )
        assert outflows[0].asset == position_asset
        assert outflows[0].reason == CashflowReason.OPERATION
        assert outflows[0].amount == Decimal("1")


# =============================================================================
# Regular Option Engine: Opening Inflows
# =============================================================================


class TestRegularOptionOpeningInflows:
    def test_open_long_empty(self, open_long_call: OrderDetails) -> None:
        assert OptionBalanceEngine.get_opening_inflows(open_long_call) == []

    def test_open_short_empty(self, open_short_call: OrderDetails) -> None:
        assert OptionBalanceEngine.get_opening_inflows(open_short_call) == []

    def test_close_long_empty(self, close_long_call: OrderDetails) -> None:
        assert OptionBalanceEngine.get_opening_inflows(close_long_call) == []

    def test_close_short_empty(self, close_short_call: OrderDetails) -> None:
        assert OptionBalanceEngine.get_opening_inflows(close_short_call) == []


# =============================================================================
# Regular Option Engine: Closing Outflows
# =============================================================================


class TestRegularOptionClosingOutflows:
    def test_open_long_empty(self, open_long_call: OrderDetails) -> None:
        """No closing outflows for OPEN action."""
        assert OptionBalanceEngine.get_closing_outflows(open_long_call) == []

    def test_open_short_empty(self, open_short_call: OrderDetails) -> None:
        assert OptionBalanceEngine.get_closing_outflows(open_short_call) == []

    def test_close_long(
        self, close_long_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """Fee only (no PnL for closing long)."""
        outflows = OptionBalanceEngine.get_closing_outflows(close_long_call)
        assert len(outflows) == 1
        assert outflows[0].reason == CashflowReason.FEE
        # 0.1% of premium (1 * 1200) = 1.2
        assert outflows[0].amount == Decimal("1.2")

    def test_close_short(
        self, close_short_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """Fee + PnL (if negative). PnL is NaN stub → fee only."""
        outflows = OptionBalanceEngine.get_closing_outflows(close_short_call)
        assert len(outflows) == 1
        assert outflows[0].reason == CashflowReason.FEE
        # 0.1% of premium (1 * 800) = 0.8
        assert outflows[0].amount == Decimal("0.8")


# =============================================================================
# Regular Option Engine: Closing Inflows
# =============================================================================


class TestRegularOptionClosingInflows:
    def test_open_long(self, open_long_call: OrderDetails) -> None:
        """Receive long position contract."""
        inflows = OptionBalanceEngine.get_closing_inflows(open_long_call)
        assert len(inflows) == 1

        position_asset = AssetFactory.get_asset(
            open_long_call.platform,
            open_long_call.trading_pair.name,
            side=DerivativeSide.LONG,
        )
        assert inflows[0].asset == position_asset
        assert inflows[0].reason == CashflowReason.OPERATION
        assert inflows[0].amount == Decimal("1")

    def test_open_short(
        self, open_short_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """Receive short position contract + premium."""
        inflows = OptionBalanceEngine.get_closing_inflows(open_short_call)
        assert len(inflows) == 2

        # Position contract
        position_asset = AssetFactory.get_asset(
            open_short_call.platform,
            open_short_call.trading_pair.name,
            side=DerivativeSide.SHORT,
        )
        assert inflows[0].asset == position_asset
        assert inflows[0].reason == CashflowReason.OPERATION
        assert inflows[0].amount == Decimal("1")

        # Premium received
        assert inflows[1].asset == quote_asset
        assert inflows[1].reason == CashflowReason.OPERATION
        assert inflows[1].amount == Decimal("1000")

    def test_close_long(
        self, close_long_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """Receive premium from selling."""
        inflows = OptionBalanceEngine.get_closing_inflows(close_long_call)
        assert len(inflows) == 1
        assert inflows[0].asset == quote_asset
        assert inflows[0].reason == CashflowReason.OPERATION
        # Premium = 1 * 1200 = 1200
        assert inflows[0].amount == Decimal("1200")

    def test_close_short(
        self, close_short_call: OrderDetails, quote_asset: Asset
    ) -> None:
        """Return margin + PnL. Both NaN since stubs."""
        inflows = OptionBalanceEngine.get_closing_inflows(close_short_call)
        assert len(inflows) == 2

        # Margin return
        assert inflows[0].reason == CashflowReason.MARGIN
        assert inflows[0].amount.is_nan()

        # PnL (NaN → included as inflow)
        assert inflows[1].reason == CashflowReason.PNL
        assert inflows[1].amount.is_nan()


# =============================================================================
# Regular Option Engine: Complete Simulation
# =============================================================================


class TestRegularOptionCompleteSimulation:
    def test_open_long(self, open_long_call: OrderDetails) -> None:
        result = OptionBalanceEngine.get_complete_simulation(open_long_call)
        assert len(result.cashflows) == 3  # 2 opening outflows + 1 closing inflow

    def test_open_short(self, open_short_call: OrderDetails) -> None:
        result = OptionBalanceEngine.get_complete_simulation(open_short_call)
        assert len(result.cashflows) == 4  # 2 opening outflows + 2 closing inflows

    def test_close_long(self, close_long_call: OrderDetails) -> None:
        result = OptionBalanceEngine.get_complete_simulation(close_long_call)
        # 1 opening outflow (position) + 1 closing outflow (fee) + 1 closing inflow (premium)
        assert len(result.cashflows) == 3

    def test_close_short(self, close_short_call: OrderDetails) -> None:
        result = OptionBalanceEngine.get_complete_simulation(close_short_call)
        # 1 opening outflow (position) + 1 closing outflow (fee) + 2 closing inflows (margin+pnl)
        assert len(result.cashflows) == 4

    def test_flip(self, flip_short_to_long_call: OrderDetails) -> None:
        result = OptionBalanceEngine.get_complete_simulation(flip_short_to_long_call)
        # CLOSE: 1+1+2=4, OPEN: 2+0+0+1=3 → total=7
        assert len(result.cashflows) == 7


# =============================================================================
# Inverse Option Engine: Premium & Fee Calculations
# =============================================================================


class TestInverseOptionPremium:
    def test_premium_calculation(self, inverse_open_long_call: OrderDetails) -> None:
        """premium = (amount * price) / index_price = (50000 * 0.02) / 50000 = 0.02."""
        premium = InverseOptionBalanceEngine._calculate_premium(inverse_open_long_call)
        assert premium == Decimal("0.02")

    def test_premium_different_index_price(
        self,
        platform: Platform,
        inverse_call_trading_pair: TradingPair,
        inverse_call_trading_rule: TradingRule,
    ) -> None:
        """premium = (50000 * 0.02) / 25000 = 0.04."""
        order = OrderDetails(
            platform=platform,
            trading_pair=inverse_call_trading_pair,
            trading_rule=inverse_call_trading_rule,
            amount=Decimal("50000"),
            price=Decimal("0.02"),
            leverage=1,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            position_action=PositionAction.OPEN,
            index_price=Decimal("25000"),
            fee=OperationFee(
                asset=None,
                amount=Decimal("0"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )
        assert InverseOptionBalanceEngine._calculate_premium(order) == Decimal("0.04")


class TestInverseOptionFee:
    def test_percentage_fee(
        self, inverse_open_long_call: OrderDetails, base_asset: Asset
    ) -> None:
        """0.1% of premium (0.02 BTC) = 0.00002 BTC."""
        fee = InverseOptionBalanceEngine._calculate_fee_amount(inverse_open_long_call)
        assert fee == Decimal("0.00002")

    def test_absolute_fee(
        self, inverse_open_long_call: OrderDetails, base_asset: Asset
    ) -> None:
        order = inverse_open_long_call.model_copy(
            update={
                "fee": OperationFee(
                    asset=base_asset,
                    amount=Decimal("0.001"),
                    fee_type=FeeType.ABSOLUTE,
                    impact_type=FeeImpactType.ADDED_TO_COSTS,
                )
            }
        )
        fee = InverseOptionBalanceEngine._calculate_fee_amount(order)
        assert fee == Decimal("0.001")


# =============================================================================
# Inverse Option Engine: Settlement Calculations
# =============================================================================


class TestInverseOptionSettlement:
    def test_call_itm_settlement(
        self,
        platform: Platform,
        inverse_call_trading_pair: TradingPair,
        inverse_call_trading_rule: TradingRule,
    ) -> None:
        """Call ITM: max(0, 1/strike - 1/spot) * contract_value.
        1/50000 - 1/60000 = 0.00002 - 0.00001667 = 0.00000333...
        * 50000 = 0.1666...
        """
        order = OrderDetails(
            platform=platform,
            trading_pair=inverse_call_trading_pair,
            trading_rule=inverse_call_trading_rule,
            amount=Decimal("50000"),
            price=Decimal("60000"),
            leverage=1,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            position_action=PositionAction.OPEN,
            index_price=Decimal("60000"),
            fee=OperationFee(
                asset=None,
                amount=Decimal("0"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )
        settlement = InverseOptionBalanceEngine._calculate_settlement(order)
        # 1/50000 - 1/60000 = (60000-50000)/(50000*60000) = 10000/3000000000
        # * 50000 = 500000000/3000000000 = 1/6
        expected = (
            Decimal("1") / Decimal("50000") - Decimal("1") / Decimal("60000")
        ) * Decimal("50000")
        assert settlement == expected

    def test_call_otm_settlement(self, inverse_open_long_call: OrderDetails) -> None:
        """Call OTM: max(0, 1/50000 - 1/50000) = 0."""
        # price=0.02 (premium, not spot), but settlement uses price as spot
        # With spot at strike, settlement is 0
        order = inverse_open_long_call.model_copy(update={"price": Decimal("50000")})
        assert InverseOptionBalanceEngine._calculate_settlement(order) == Decimal("0")

    def test_put_itm_settlement(
        self,
        platform: Platform,
        inverse_put_trading_pair: TradingPair,
        inverse_put_trading_rule: TradingRule,
    ) -> None:
        """Put ITM: max(0, 1/spot - 1/strike) * contract_value."""
        order = OrderDetails(
            platform=platform,
            trading_pair=inverse_put_trading_pair,
            trading_rule=inverse_put_trading_rule,
            amount=Decimal("50000"),
            price=Decimal("40000"),
            leverage=1,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            position_action=PositionAction.OPEN,
            index_price=Decimal("40000"),
            fee=OperationFee(
                asset=None,
                amount=Decimal("0"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )
        settlement = InverseOptionBalanceEngine._calculate_settlement(order)
        expected = (
            Decimal("1") / Decimal("40000") - Decimal("1") / Decimal("50000")
        ) * Decimal("50000")
        assert settlement == expected
        assert settlement > 0


# =============================================================================
# Inverse Option Engine: Outflow Asset
# =============================================================================


class TestInverseOptionOutflowAsset:
    def test_outflow_asset_is_base(
        self, inverse_open_long_call: OrderDetails, base_asset: Asset
    ) -> None:
        """Inverse options use base currency (BTC) as collateral."""
        assert (
            InverseOptionBalanceEngine._get_outflow_asset(inverse_open_long_call)
            == base_asset
        )


# =============================================================================
# Inverse Option Engine: Opening Outflows
# =============================================================================


class TestInverseOptionOpeningOutflows:
    def test_open_long(
        self, inverse_open_long_call: OrderDetails, base_asset: Asset
    ) -> None:
        """Premium + fee in BTC."""
        outflows = InverseOptionBalanceEngine.get_opening_outflows(
            inverse_open_long_call
        )
        assert len(outflows) == 2

        # Premium: (50000 * 0.02) / 50000 = 0.02 BTC
        assert outflows[0].asset == base_asset
        assert outflows[0].reason == CashflowReason.OPERATION
        assert outflows[0].amount == Decimal("0.02")

        # Fee: 0.1% of 0.02 = 0.00002 BTC
        assert outflows[1].reason == CashflowReason.FEE
        assert outflows[1].amount == Decimal("0.00002")

    def test_open_short(
        self, inverse_open_short_call: OrderDetails, base_asset: Asset
    ) -> None:
        """Margin + fee."""
        outflows = InverseOptionBalanceEngine.get_opening_outflows(
            inverse_open_short_call
        )
        assert len(outflows) == 2

        # Margin (NaN stub)
        assert outflows[0].reason == CashflowReason.MARGIN
        assert outflows[0].amount.is_nan()

        # Fee
        assert outflows[1].reason == CashflowReason.FEE
        assert outflows[1].amount == Decimal("0.00002")


# =============================================================================
# Inverse Option Engine: Closing Inflows
# =============================================================================


class TestInverseOptionClosingInflows:
    def test_open_long(self, inverse_open_long_call: OrderDetails) -> None:
        """Receive position contract."""
        inflows = InverseOptionBalanceEngine.get_closing_inflows(inverse_open_long_call)
        assert len(inflows) == 1
        assert inflows[0].reason == CashflowReason.OPERATION
        assert inflows[0].amount == Decimal("50000")

    def test_open_short(
        self, inverse_open_short_call: OrderDetails, base_asset: Asset
    ) -> None:
        """Receive position contract + premium in BTC."""
        inflows = InverseOptionBalanceEngine.get_closing_inflows(
            inverse_open_short_call
        )
        assert len(inflows) == 2

        # Position
        assert inflows[0].reason == CashflowReason.OPERATION
        assert inflows[0].amount == Decimal("50000")

        # Premium
        assert inflows[1].asset == base_asset
        assert inflows[1].reason == CashflowReason.OPERATION
        assert inflows[1].amount == Decimal("0.02")


# =============================================================================
# FLIP via split
# =============================================================================


class TestFlipSplit:
    def test_flip_splits_into_close_and_open(
        self, flip_short_to_long_call: OrderDetails
    ) -> None:
        """FLIP with amount=2, position=1 splits into CLOSE(1) + OPEN(1)."""
        parts = flip_short_to_long_call.split_order_details()
        assert len(parts) == 2

        close_part = parts[0]
        assert close_part.position_action == PositionAction.CLOSE
        assert close_part.amount == Decimal("1")

        open_part = parts[1]
        assert open_part.position_action == PositionAction.OPEN
        assert open_part.amount == Decimal("1")

    def test_flip_opening_outflows(self, flip_short_to_long_call: OrderDetails) -> None:
        """FLIP opening outflows = close outflows + open outflows."""
        outflows = OptionBalanceEngine.get_opening_outflows(flip_short_to_long_call)
        # CLOSE BUY: 1 (position delivery) + OPEN BUY: 2 (premium + fee) = 3
        assert len(outflows) == 3

    def test_flip_opening_inflows(self, flip_short_to_long_call: OrderDetails) -> None:
        """FLIP opening inflows are always empty."""
        inflows = OptionBalanceEngine.get_opening_inflows(flip_short_to_long_call)
        assert len(inflows) == 0

    def test_flip_closing_inflows(self, flip_short_to_long_call: OrderDetails) -> None:
        """FLIP closing inflows = close inflows + open inflows."""
        inflows = OptionBalanceEngine.get_closing_inflows(flip_short_to_long_call)
        # CLOSE BUY: 2 (margin + pnl) + OPEN BUY: 1 (position) = 3
        assert len(inflows) == 3


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    def test_zero_fee(
        self,
        platform: Platform,
        call_trading_pair: TradingPair,
        call_trading_rule: TradingRule,
        quote_asset: Asset,
    ) -> None:
        """Zero percentage fee should produce zero fee amount."""
        order = OrderDetails(
            platform=platform,
            trading_pair=call_trading_pair,
            trading_rule=call_trading_rule,
            amount=Decimal("1"),
            price=Decimal("1000"),
            leverage=1,
            trade_type=TradeType.BUY,
            order_type=OrderType.LIMIT,
            position_action=PositionAction.OPEN,
            index_price=Decimal("50000"),
            fee=OperationFee(
                asset=quote_asset,
                amount=Decimal("0"),
                fee_type=FeeType.PERCENTAGE,
                impact_type=FeeImpactType.ADDED_TO_COSTS,
            ),
        )
        fee = OptionBalanceEngine._calculate_fee_amount(order)
        assert fee == Decimal("0")

    def test_margin_returns_nan(self, open_short_call: OrderDetails) -> None:
        """Margin calculation is a stub returning NaN."""
        margin = OptionBalanceEngine._calculate_margin(open_short_call)
        assert margin.is_nan()

    def test_pnl_returns_nan(self, open_long_call: OrderDetails) -> None:
        """PnL calculation is a stub returning NaN."""
        pnl = OptionBalanceEngine._calculate_pnl(open_long_call)
        assert pnl.is_nan()

    def test_inverse_margin_returns_nan(
        self, inverse_open_short_call: OrderDetails
    ) -> None:
        margin = InverseOptionBalanceEngine._calculate_margin(inverse_open_short_call)
        assert margin.is_nan()

    def test_inverse_pnl_returns_nan(
        self, inverse_open_long_call: OrderDetails
    ) -> None:
        pnl = InverseOptionBalanceEngine._calculate_pnl(inverse_open_long_call)
        assert pnl.is_nan()

    def test_index_price_not_implemented(self, open_long_call: OrderDetails) -> None:
        with pytest.raises(NotImplementedError):
            OptionBalanceEngine._calculate_index_price(open_long_call)

    def test_inverse_index_price_not_implemented(
        self, inverse_open_long_call: OrderDetails
    ) -> None:
        with pytest.raises(NotImplementedError):
            InverseOptionBalanceEngine._calculate_index_price(inverse_open_long_call)

    def test_liquidation_price_not_implemented(
        self, open_long_call: OrderDetails
    ) -> None:
        with pytest.raises(NotImplementedError):
            OptionBalanceEngine._calculate_liquidation_price(open_long_call)
