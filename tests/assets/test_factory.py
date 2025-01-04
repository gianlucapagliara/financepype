from typing import Any
from unittest.mock import Mock, PropertyMock

from financepype.assets.asset import Asset
from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.assets.factory import AssetFactory
from financepype.assets.spot import SpotAsset
from financepype.markets.market import InstrumentType
from financepype.platforms.platform import Platform


def test_get_spot_asset(platform: Platform) -> None:
    """Test creating a spot asset."""
    asset = AssetFactory.get_asset(platform, "BTC")
    assert isinstance(asset, SpotAsset)
    assert asset.symbol == "BTC"
    assert asset.platform == platform


def test_get_derivative_asset(platform: Platform) -> None:
    """Test creating a derivative asset."""
    # Using a valid derivative symbol format
    long_asset = AssetFactory.get_asset(
        platform, "BTC-USD-PERPETUAL", side=DerivativeSide.LONG
    )
    assert isinstance(long_asset, DerivativeContract)
    assert long_asset.trading_pair.name == "BTC-USD-PERPETUAL"
    assert long_asset.platform == platform
    assert long_asset.side == DerivativeSide.LONG

    short_asset = AssetFactory.get_asset(
        platform, "BTC-USD-PERPETUAL", side=DerivativeSide.SHORT
    )
    assert isinstance(short_asset, DerivativeContract)
    assert short_asset.trading_pair.name == "BTC-USD-PERPETUAL"
    assert short_asset.platform == platform
    assert short_asset.side == DerivativeSide.SHORT

    assert long_asset != short_asset
    assert long_asset.trading_pair.name == short_asset.trading_pair.name
    assert long_asset.platform == short_asset.platform


def test_asset_caching(platform: Platform) -> None:
    """Test that assets are cached and reused."""
    asset1 = AssetFactory.get_asset(platform, "BTC")
    asset2 = AssetFactory.get_asset(platform, "BTC")
    assert asset1 is asset2  # Same instance


def test_asset_caching_with_different_platforms() -> None:
    """Test that assets with the same symbol but different platforms are cached separately."""
    platform1 = Platform(identifier="platform1")
    platform2 = Platform(identifier="platform2")

    asset1 = AssetFactory.get_asset(platform1, "BTC")
    asset2 = AssetFactory.get_asset(platform2, "BTC")
    asset3 = AssetFactory.get_asset(platform1, "BTC")

    assert asset1 is not asset2  # Different platforms should create different instances
    assert asset1 is asset3  # Same platform should reuse the instance
    assert asset1.platform is platform1
    assert asset2.platform is platform2


def test_custom_asset_creation(platform: Platform) -> None:
    """Test registering and using a custom asset creator."""
    # Create a mock asset with the required attributes
    custom_asset = Mock(spec=Asset)
    custom_asset.platform = None

    # Mock the identifier property
    identifier = PropertyMock(return_value=AssetIdentifier(value="CUSTOM-USD-SPOT"))
    type(custom_asset).identifier = identifier

    # Define a custom creator function
    def custom_creator(p: Platform, s: str, _: Any) -> Asset:
        custom_asset.platform = p
        identifier.return_value = AssetIdentifier(value=s)
        return custom_asset

    # Register the custom creator
    AssetFactory.register_creator(InstrumentType.SPOT, custom_creator)

    # Create an asset using the custom creator
    asset = AssetFactory.get_asset(platform, "CUSTOM-USD-SPOT")

    # Verify the asset was created correctly
    assert asset is custom_asset
    assert asset.platform == platform
    assert str(asset.identifier) == "CUSTOM-USD-SPOT"
