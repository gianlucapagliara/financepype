from pydantic import BaseModel, ConfigDict


class AssetIdentifier(BaseModel):
    """An immutable identifier for assets in the trading system.

    This class provides a standardized way to identify assets across different
    platforms. The identifier is immutable to ensure consistency and can be
    safely used as a dictionary key or in sets.

    Attributes:
        value (str): The string value of the asset identifier

    Example:
        >>> btc_id = AssetIdentifier(value="BTC")
        >>> usdt_id = AssetIdentifier(value="USDT")
        >>> assert btc_id != usdt_id
        >>> asset_map = {btc_id: "Bitcoin"}  # Can be used as dict key
    """

    model_config = ConfigDict(frozen=True)

    value: str

    def __str__(self) -> str:
        """Get the string representation of the asset identifier.

        Returns:
            str: The identifier value
        """
        return self.value

    def __repr__(self) -> str:
        """Get the detailed string representation of the asset identifier.

        Returns:
            str: Detailed representation including class name and value
        """
        return f"AssetIdentifier(value={self.value})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AssetIdentifier):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)
