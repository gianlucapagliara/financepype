from typing import Any

from pydantic import BaseModel, ConfigDict

from financepype.platforms.platform import Platform


class Asset(BaseModel):
    """Abstract base class representing a tradable asset within the system.

    This class provides the foundation for all asset types in the trading system.
    Assets are immutable and uniquely identified by their platform and identifier.
    The class implements proper equality and hashing to ensure consistent behavior
    when used in collections.

    Attributes:
        platform (Platform): The trading platform where this asset exists
        identifier (AssetIdentifier): Unique identifier for the asset on the platform

    Note:
        Assets are immutable (frozen) by design to ensure thread safety and
        consistent behavior in collections.

    Example:
        >>> from financepype.platforms.platform import Platform
        >>> from financepype.assets.spot import SpotAsset
        >>> btc = SpotAsset(platform=Platform("binance"), identifier="BTC")
        >>> eth = SpotAsset(platform=Platform("binance"), identifier="ETH")
        >>> assert btc != eth
        >>> assets = {btc, eth}  # Can be used in sets
    """

    model_config = ConfigDict(frozen=True)

    platform: Platform
    identifier: Any
