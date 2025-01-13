from decimal import Decimal

import pandas as pd
import streamlit as st

from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import OrderType, PositionAction, TradeType
from financepype.platforms.centralized import CentralizedPlatform
from financepype.rules.trading_rule import DerivativeTradingRule, TradingRule
from financepype.simulations.balances.engines.models import AssetCashflow, OrderDetails
from financepype.simulations.balances.engines.multiengine import BalanceMultiEngine


def create_sample_order(
    trade_type: TradeType,
    position_action: PositionAction,
    amount: Decimal,
    price: Decimal,
    platform_id: str = "binance",
    trading_pair: str = "EXAMPLE-USDT",
    fee_type: FeeType = FeeType.PERCENTAGE,
    fee_impact: FeeImpactType = FeeImpactType.ADDED_TO_COSTS,
    fee_amount: Decimal = Decimal("0.1"),
) -> OrderDetails:
    """Create a sample order for simulation."""
    platform = CentralizedPlatform(identifier=platform_id)

    trading_pair_obj = TradingPair(name=trading_pair)

    if trading_pair_obj.market_info.is_spot:
        trading_rule = TradingRule(
            trading_pair=trading_pair_obj,
            min_order_size=Decimal("0.0001"),
            min_price_increment=Decimal("0.01"),
            min_notional_size=Decimal("10"),
        )
    else:
        trading_rule = DerivativeTradingRule(
            trading_pair=trading_pair_obj,
            min_order_size=Decimal("0.0001"),
            min_price_increment=Decimal("0.01"),
            min_notional_size=Decimal("10"),
        )

    return OrderDetails(
        platform=platform,
        trading_pair=trading_pair_obj,
        trading_rule=trading_rule,
        trade_type=trade_type,
        order_type=OrderType.MARKET,
        amount=amount,
        price=price,
        leverage=1,
        position_action=position_action,
        entry_index_price=price,
        fee=OperationFee(
            asset=None,
            fee_type=fee_type,
            impact_type=fee_impact,
            amount=fee_amount,
        ),
    )


def format_cashflows(cashflows: list[AssetCashflow]) -> pd.DataFrame:
    """Format cashflows into a DataFrame for visualization."""
    data = []
    for cf in cashflows:
        data.append(
            {
                "Asset": cf.asset.identifier.value,
                "Phase": cf.involvement_type.value,
                "Type": cf.cashflow_type.value,
                "Reason": cf.reason.value,
                "Amount": cf.amount if cf.amount else "TBD",
            }
        )
    return pd.DataFrame(data)


def main() -> None:
    st.title("Trading Cashflow Simulator")

    # Sidebar for input parameters
    st.sidebar.header("Trading Parameters")

    trade_type = st.sidebar.selectbox(
        "Trade Type",
        options=[TradeType.BUY, TradeType.SELL],
    )

    position_action = st.sidebar.selectbox(
        "Position Action",
        options=[
            PositionAction.NIL,
            PositionAction.OPEN,
            PositionAction.CLOSE,
            PositionAction.FLIP,
        ],
    )

    trading_pair = st.sidebar.text_input("Trading Pair", value="EXAMPLE-USDT")
    amount = st.sidebar.number_input("Amount", value=1.0, step=0.1)
    price = st.sidebar.number_input("Price", value=100.0, step=100.0)

    # Fee settings
    st.sidebar.header("Fee Settings")
    fee_type = st.sidebar.selectbox(
        "Fee Type",
        options=[FeeType.PERCENTAGE, FeeType.ABSOLUTE],
    )

    fee_impact = st.sidebar.selectbox(
        "Fee Impact",
        options=[FeeImpactType.ADDED_TO_COSTS, FeeImpactType.DEDUCTED_FROM_RETURNS],
    )

    fee_amount = st.sidebar.number_input(
        "Fee Amount (% or absolute)",
        value=0.1,
        step=0.01,
    )

    # Create order and simulate cashflows
    order = create_sample_order(
        trade_type=trade_type,
        position_action=position_action,
        amount=Decimal(str(amount)),
        price=Decimal(str(price)),
        platform_id="binance",
        trading_pair=trading_pair,
        fee_type=fee_type,
        fee_impact=fee_impact,
        fee_amount=(
            Decimal(str(fee_amount))
            if fee_type == FeeType.PERCENTAGE
            else Decimal(str(fee_amount))
        ),
    )

    # Display order details
    st.header("Order Details")
    with st.expander("Order Details", expanded=False):
        st.json(
            {
                "Platform": order.platform.identifier,
                "Trading Pair": order.trading_pair.name,
                "Trade Type": order.trade_type.value,
                "Position Action": order.position_action.value,
                "Amount": str(order.amount),
                "Price": str(order.price),
                "Fee Type": order.fee.fee_type.value,
                "Fee Impact": order.fee.impact_type.value,
                "Fee Amount": str(order.fee.amount),
            }
        )

    # Add explanatory notes
    st.header("Simulation")

    with st.expander("Notes", expanded=False):
        st.markdown(
            """
            - **Opening Outflows**: Assets leaving your account when placing the order
            - **Opening Inflows**: Assets entering your account when placing the order
            - **Closing Outflows**: Assets leaving your account when completing the order
            - **Closing Inflows**: Assets entering your account when completing the order

            Reasons for cashflows:
            - **OPERATION**: Regular trading operation costs/returns
            - **FEE**: Trading fees
            - **PNL**: Profit and Loss
            """
        )

    # Get involved assets
    engine = BalanceMultiEngine()

    # Involved assets
    cashflow_assets = engine.get_involved_assets(order)
    involved_assets = [cashflow.asset for cashflow in cashflow_assets]
    st.subheader("Involved Assets")
    st.json(involved_assets)

    # Complete simulation
    simulation = engine.get_complete_simulation(order)

    # Display cashflow simulation
    st.subheader("Cashflow Simulation")
    df = format_cashflows(simulation.cashflows)
    st.dataframe(df)


if __name__ == "__main__":
    main()
