from datetime import datetime, timedelta
from decimal import Decimal
from typing import cast

import pandas as pd
import streamlit as st

from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.assets.factory import AssetFactory
from financepype.markets.market import (
    InstrumentTimeframeType,
    InstrumentType,
    MarketInfo,
)
from financepype.markets.position import Position
from financepype.markets.trading_pair import TradingPair
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.orders.models import OrderType, PositionAction, TradeType
from financepype.platforms.centralized import CentralizedPlatform
from financepype.rules.trading_rule import DerivativeTradingRule, TradingRule
from financepype.simulations.balances.engines.models import (
    AssetCashflow,
    InvolvementType,
    OrderDetails,
)
from financepype.simulations.balances.engines.multiengine import BalanceMultiEngine


def format_cashflows(cashflows: list[AssetCashflow]) -> pd.DataFrame:
    """Format cashflows into a DataFrame for visualization."""
    data = []
    for cf in cashflows:
        data.append(
            {
                "Asset": f"{cf.asset.side.value}:{cf.asset.identifier.value}"
                if isinstance(cf.asset, DerivativeContract)
                else cf.asset.identifier.value,
                "Phase": cf.involvement_type.value,
                "Type": cf.cashflow_type.value,
                "Reason": cf.reason.value,
                "Amount": cf.amount,
            }
        )
    return pd.DataFrame(data, columns=["Asset", "Phase", "Type", "Reason", "Amount"])


def main() -> None:
    st.set_page_config(page_title="Cashflow Simulator", layout="wide")
    st.title("Cashflow Simulator")

    st.sidebar.header("Market")
    base = st.sidebar.text_input("Base", value="EXAMPLE")
    quote = st.sidebar.text_input("Quote", value="USDT")
    instrument_type = st.sidebar.selectbox(
        "Instrument Type",
        options=[
            InstrumentType.SPOT,
            InstrumentType.PERPETUAL,
            InstrumentType.INVERSE_PERPETUAL,
            InstrumentType.CALL_OPTION,
            InstrumentType.PUT_OPTION,
            InstrumentType.INVERSE_CALL_OPTION,
            InstrumentType.INVERSE_PUT_OPTION,
        ],
    )
    timeframe_type = None
    expiry_date = None
    strike_price = None
    if instrument_type.is_option:
        timeframe_type = InstrumentTimeframeType.WEEKLY
        expiry_date = datetime.now() + timedelta(days=30)
        strike_price = st.sidebar.number_input("Strike Price", value=100.0, step=5.0)
    market_info = MarketInfo(
        base=base,
        quote=quote,
        instrument_type=instrument_type,
        timeframe_type=timeframe_type,
        expiry_date=expiry_date,
        strike_price=Decimal(str(strike_price)) if strike_price else None,
    )
    trading_pair = market_info.client_name

    # Sidebar for input parameters
    st.sidebar.header("Trading Parameters")
    platform = CentralizedPlatform(identifier="exchange")
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
        index=0 if trading_pair_obj.market_info.is_spot else 1,
    )
    amount = st.sidebar.number_input("Amount", value=1.0, step=1.0)
    price = st.sidebar.number_input("Price", value=100.0, step=5.0)
    index_price = None
    leverage = 1
    if trading_pair_obj.market_info.is_derivative:
        index_price = st.sidebar.number_input("Index Price", value=100.0, step=5.0)
        leverage = st.sidebar.number_input("Leverage", value=1, step=1)

    current_position = None
    if position_action not in [PositionAction.NIL, PositionAction.OPEN]:
        st.sidebar.header("Open Position")
        open_position_side = st.sidebar.selectbox(
            "Open Position Side",
            options=[DerivativeSide.LONG, DerivativeSide.SHORT],
            index=0 if trade_type == TradeType.SELL else 1,
        )
        open_position_amount = st.sidebar.number_input(
            "Open Position Amount", value=amount, step=1.0
        )
        open_position_price = st.sidebar.number_input(
            "Open Position Price", value=price / 2, step=5.0
        )
        open_position_index_price = st.sidebar.number_input(
            "Open Position Index Price",
            value=index_price / 2 if index_price else 0,
            step=5.0,
        )
        open_position_margin = st.sidebar.number_input(
            "Open Position Margin", value=100.0, step=5.0
        )
        contract = cast(
            DerivativeContract,
            AssetFactory.get_asset(
                platform=platform,
                symbol=trading_pair_obj.name,
                side=open_position_side,
            ),
        )
        current_position = Position(
            asset=contract,
            amount=Decimal(str(open_position_amount)),
            leverage=Decimal(str(leverage)),
            entry_price=Decimal(str(open_position_price)),
            entry_index_price=Decimal(str(open_position_index_price)),
            margin=Decimal(str(open_position_margin)),
            unrealized_pnl=Decimal("0"),
            liquidation_price=Decimal("0"),
        )

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
        "Fee Amount (% or absolute)", value=0.1, step=0.01
    )

    fee = OperationFee(
        asset=None,
        fee_type=fee_type,
        impact_type=fee_impact,
        amount=Decimal(str(fee_amount)),
    )

    order = OrderDetails(
        platform=platform,
        trading_pair=trading_pair_obj,
        trading_rule=trading_rule,
        trade_type=trade_type,
        order_type=OrderType.MARKET,
        amount=Decimal(str(amount)),
        price=Decimal(str(price)),
        index_price=Decimal(str(index_price)) if index_price else None,
        leverage=leverage,
        position_action=position_action,
        current_position=current_position,
        fee=fee,
    )

    # Display order details
    st.header("Order Details")
    with st.expander("Order Details", expanded=False):
        st.json(order.model_dump(mode="json"))

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
    opening_inflows = [
        cashflow
        for cashflow in simulation.cashflows
        if cashflow.involvement_type == InvolvementType.OPENING and cashflow.is_inflow
    ]
    opening_outflows = [
        cashflow
        for cashflow in simulation.cashflows
        if cashflow.involvement_type == InvolvementType.OPENING and cashflow.is_outflow
    ]
    closing_inflows = [
        cashflow
        for cashflow in simulation.cashflows
        if cashflow.involvement_type == InvolvementType.CLOSING and cashflow.is_inflow
    ]
    closing_outflows = [
        cashflow
        for cashflow in simulation.cashflows
        if cashflow.involvement_type == InvolvementType.CLOSING and cashflow.is_outflow
    ]

    # Display cashflow simulation
    st.subheader("Cashflow Simulation")
    st.write("Opening")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Inflows")
        df = format_cashflows(opening_inflows)
        st.dataframe(df, hide_index=True, use_container_width=True)
    with col2:
        st.write("Outflows")
        df = format_cashflows(opening_outflows)
        st.dataframe(df, hide_index=True, use_container_width=True)

    st.write("Closing")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Inflows")
        df = format_cashflows(closing_inflows)
        st.dataframe(df, hide_index=True, use_container_width=True)
    with col2:
        st.write("Outflows")
        df = format_cashflows(closing_outflows)
        st.dataframe(df, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
