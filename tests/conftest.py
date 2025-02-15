from collections.abc import Generator

import pytest

from financepype.assets.asset import Asset
from financepype.assets.factory import AssetFactory
from financepype.operators.factory import OperatorFactory
from financepype.platforms.platform import Platform


@pytest.fixture(autouse=True)
def clear_caches() -> Generator[None, None, None]:
    """Clear all caches before each test."""
    # Reset AssetFactory to its initial state
    AssetFactory.reset()
    OperatorFactory.reset()
    Platform.clear_cache()
    yield


@pytest.fixture
def platform() -> Platform:
    """Fixture providing a test platform instance."""
    return Platform(identifier="test_platform")


@pytest.fixture
def btc_asset(platform: Platform) -> Asset:
    return AssetFactory.get_asset(platform, "BTC")


@pytest.fixture
def usdt_asset(platform: Platform) -> Asset:
    return AssetFactory.get_asset(platform, "USDT")


@pytest.fixture
def test_asset(platform: Platform) -> Asset:
    return AssetFactory.get_asset(platform, "TEST")
