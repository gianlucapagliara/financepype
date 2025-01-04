from decimal import Decimal

import pytest
from pydantic import BaseModel, ConfigDict

from financepype.assets.asset import Asset
from financepype.assets.spot import SpotAsset
from financepype.markets.trading_pair import TradingPair
from financepype.rules.trading_rule import TradingRule


class MockBalances(BaseModel):
    """Helper class for test balances to ensure hashable assets."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    balances: dict[str, Decimal]

    def get_balances(self, assets: list[Asset]) -> dict[Asset, Decimal]:
        """Get balances for a list of assets."""
        return {
            asset: self.balances.get(str(asset.identifier), Decimal("0"))
            for asset in assets
        }

    def set_balance(self, asset: Asset, amount: Decimal) -> None:
        """Set balance for an asset."""
        self.balances[str(asset.identifier)] = amount


@pytest.fixture
def spot_trading_rule(btc_asset: SpotAsset, usdt_asset: SpotAsset) -> TradingRule:
    """Create a spot trading rule for BTC-USDT."""
    return TradingRule(
        trading_pair=TradingPair(name="BTC-USDT"),
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100"),
        min_price_increment=Decimal("0.1"),
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
    )


@pytest.fixture
def perpetual_trading_rule(btc_asset: SpotAsset, usdt_asset: SpotAsset) -> TradingRule:
    """Create a perpetual trading rule for BTC-USDT-PERPETUAL."""
    return TradingRule(
        trading_pair=TradingPair(name="BTC-USDT-PERPETUAL"),
        min_order_size=Decimal("0.001"),
        max_order_size=Decimal("100"),
        min_price_increment=Decimal("0.1"),
        min_base_amount_increment=Decimal("0.001"),
        min_quote_amount_increment=Decimal("0.01"),
    )


@pytest.fixture
def test_balances() -> MockBalances:
    """Create test balances with initial values."""
    return MockBalances(
        balances={
            "BTC": Decimal("10"),
            "USDT": Decimal("100000"),
        }
    )
