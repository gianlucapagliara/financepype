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

    def __eq__(self, other: object) -> bool:
        """Compare this identifier with another for equality.

        Args:
            other: The object to compare with

        Returns:
            bool: True if the other object is an AssetIdentifier with the same value
        """
        if not isinstance(other, AssetIdentifier):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Get the hash value of the identifier.

        The hash is based on the identifier value to ensure consistency
        with equality comparison.

        Returns:
            int: Hash value of the identifier
        """
        return hash(self.value)
