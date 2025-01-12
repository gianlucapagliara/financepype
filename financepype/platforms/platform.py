from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_platform_cache: dict[str, "Platform"] = {}
"""Global cache of platform instances to ensure uniqueness."""


class Platform(BaseModel):
    """An immutable class representing a trading platform or exchange.

    This class provides a standardized way to identify and reference different
    trading platforms within the system. Platform instances are immutable to
    ensure consistency across the application. The class implements a caching
    mechanism to ensure that only one instance exists for each platform identifier.

    The class uses Pydantic for validation and immutability, ensuring that
    platform instances cannot be modified after creation.

    Attributes:
        identifier (str): A unique identifier for the platform (e.g., "binance", "kraken")
        model_config (ConfigDict): Pydantic configuration for immutability

    Example:
        >>> binance = Platform(identifier="binance")
        >>> kraken = Platform(identifier="kraken")
        >>> assert binance != kraken
        >>> assert hash(binance) != hash(kraken)
        >>> binance2 = Platform(identifier="binance")
        >>> assert binance is binance2  # Same instance due to caching
    """

    model_config = ConfigDict(frozen=True)

    identifier: str = Field(
        min_length=1,
        description="Unique identifier for the platform. Must be non-empty.",
    )

    def __new__(cls, **data: Any) -> "Platform":
        """Create or retrieve a cached platform instance.

        This method implements the caching mechanism. If a platform with the
        given identifier already exists in the cache, that instance is returned.
        Otherwise, a new instance is created and cached.

        Args:
            **data: Keyword arguments including 'identifier' for the platform

        Returns:
            Platform: A new or cached platform instance
        """
        identifier = data.get("identifier")
        if identifier is None:
            # Let Pydantic handle validation
            instance = super().__new__(cls)
            return instance

        cache_key = f"{cls.__name__}:{identifier}"
        for key, value in sorted(data.items()):
            if key != "identifier":
                cache_key += f":{key}={value}"

        if cache_key in _platform_cache:
            return _platform_cache[cache_key]

        instance = super().__new__(cls)
        return instance

    def __init__(self, **data: Any) -> None:
        """Initialize a platform instance.

        This method initializes the platform and adds it to the cache.
        Due to the caching mechanism in __new__, this will only be called
        for new platform instances.

        Args:
            **data: Keyword arguments including 'identifier' for the platform
        """
        super().__init__(**data)
        if self.identifier:  # Only cache if identifier is valid
            cache_key = f"{self.__class__.__name__}:{self.identifier}"
            for key, value in sorted(data.items()):
                if key != "identifier":
                    cache_key += f":{key}={value}"
            _platform_cache[cache_key] = self

    def __str__(self) -> str:
        """Get the string representation of the platform.

        Returns:
            str: The platform identifier

        Example:
            >>> platform = Platform(identifier="binance")
            >>> str(platform)  # Returns: "binance"
        """
        return self.identifier

    def __repr__(self) -> str:
        """Get the detailed string representation of the platform.

        Returns:
            str: A detailed representation including the class name

        Example:
            >>> platform = Platform(identifier="binance")
            >>> repr(platform)  # Returns: "<Platform: binance>"
        """
        return f"<{self.__class__.__name__}: {self.identifier}>"

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the platform cache.

        This method removes all cached platform instances. After calling this,
        new instances will be created for any platform identifiers, even if
        they were previously cached.

        This is primarily useful for testing scenarios where you want to
        ensure a clean state.
        """
        _platform_cache.clear()
