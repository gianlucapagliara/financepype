from pydantic import ConfigDict, Field

from financepype.assets.centralized_asset import CentralizedAsset


class SpotAsset(CentralizedAsset):
    """Represents a spot trading asset in the system.

    A spot asset is a basic tradable asset that can be bought or sold
    immediately at the current market price. This class extends the base
    Asset class to provide spot-specific functionality.

    Attributes:
        platform (Platform): The platform where this asset trades (inherited from Asset)
        identifier (AssetIdentifier): Unique identifier for the asset (inherited from Asset)
        name (str | None): Optional human-readable name for the asset (e.g., "Bitcoin")

    Properties:
        symbol (str): The trading symbol for the asset (e.g., "BTC", "ETH")

    Example:
        >>> from financepype.platforms.platform import Platform
        >>> from financepype.assets.asset_id import AssetIdentifier
        >>> btc = SpotAsset(
        ...     platform=Platform("binance"),
        ...     identifier=AssetIdentifier(value="BTC"),
        ...     name="Bitcoin"
        ... )
        >>> print(btc.symbol)  # Outputs: BTC
        >>> print(btc.name)    # Outputs: Bitcoin
    """

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(
        default=None, description="The human-readable name for the asset"
    )
