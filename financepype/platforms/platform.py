from pydantic import BaseModel, ConfigDict, Field

_platform_cache: dict[str, "Platform"] = {}


class Platform(BaseModel):
    """An immutable class representing a trading platform or exchange.

    This class provides a standardized way to identify and reference different
    trading platforms within the system. Platform instances are immutable to
    ensure consistency across the application.

    Attributes:
        identifier (str): A unique identifier for the platform (e.g., "binance", "kraken")

    Example:
        >>> binance = Platform(identifier="binance")
        >>> kraken = Platform(identifier="kraken")
        >>> assert binance != kraken
        >>> assert hash(binance) != hash(kraken)
    """

    model_config = ConfigDict(frozen=True)

    identifier: str = Field(min_length=1)

    def __new__(cls, identifier: str) -> "Platform":
        """Create or retrieve a cached platform instance.

        Args:
            identifier: The platform identifier

        Returns:
            Platform: A new or cached platform instance
        """
        if identifier in _platform_cache:
            return _platform_cache[identifier]
        instance = super().__new__(cls)
        return instance

    def __init__(self, identifier: str) -> None:
        """Initialize a platform instance.

        Args:
            identifier: The platform identifier
        """
        super().__init__(identifier=identifier)
        _platform_cache[identifier] = self

    def __str__(self) -> str:
        """Get the string representation of the platform.

        Returns:
            str: The platform identifier
        """
        return self.identifier

    def __repr__(self) -> str:
        """Get the detailed string representation of the platform.

        Returns:
            str: A detailed representation including the class name
        """
        return f"<{self.__class__.__name__}: {self.identifier}>"

    def __eq__(self, other: object) -> bool:
        """Compare this platform with another object for equality.

        Args:
            other: The object to compare with

        Returns:
            bool: True if the other object is a Platform with the same identifier
        """
        if not isinstance(other, Platform):
            return False
        return self.identifier == other.identifier

    def __hash__(self) -> int:
        """Get the hash value of the platform.

        The hash is based on the platform identifier to ensure consistency
        with the equality comparison.

        Returns:
            int: Hash value of the platform
        """
        return hash(self.identifier)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the platform cache."""
        _platform_cache.clear()
