from pydantic import ConfigDict, Field

from financepype.assets.asset import Asset


class SpotAsset(Asset):
    """Represents a spot trading asset in the system.

    A spot asset is a basic tradable asset that can be bought or sold
    immediately at the current market price. This class extends the base
    Asset class to provide spot-specific functionality.

    Attributes:
        symbol (str): The trading symbol for the asset (e.g., "BTC", "ETH")
        name (str | None): Optional human-readable name for the asset
        platform (Platform): Inherited from Asset, the platform where this asset trades

    Example:
        >>> btc = SpotAsset(
        ...     platform=Platform("binance"),
        ...     symbol="BTC",
        ...     name="Bitcoin"
        ... )
        >>> print(btc.identifier)  # Outputs: BTC
    """

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(
        default=None, description="The human-readable name for the asset"
    )

    @property
    def symbol(self) -> str:
        return self.identifier.value
