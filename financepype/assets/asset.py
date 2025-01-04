from pydantic import BaseModel, ConfigDict

from financepype.assets.asset_id import AssetIdentifier
from financepype.platforms.platform import Platform


class Asset(BaseModel):
    """Abstract base class representing a tradable asset within the system.

    This class provides the foundation for all asset types in the trading system.
    Assets are immutable and uniquely identified by their platform and identifier.
    The class implements proper equality and hashing to ensure consistent behavior
    when used in collections.

    Attributes:
        platform (Platform): The trading platform where this asset exists

    Example:
        >>> btc = SpotAsset(platform=Platform("binance"), ...)
        >>> eth = SpotAsset(platform=Platform("binance"), ...)
        >>> assert btc != eth
        >>> assets = {btc, eth}  # Can be used in sets
    """

    model_config = ConfigDict(frozen=True)

    platform: Platform
    identifier: AssetIdentifier
