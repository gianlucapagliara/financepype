from typing import Any

from financepype.platforms.platform import Platform


class OwnerIdentifier:
    """Unique identifier for trading account owners.

    This class represents a unique identifier for trading account owners
    across different platforms. It combines a platform-specific name with
    the platform identifier to ensure uniqueness.

    The identifier is immutable and can be safely used as a dictionary key
    or in sets. It implements proper equality and hashing behavior.

    Attributes:
        name (str): Platform-specific owner name
        platform (Platform): The platform this owner belongs to
        identifier (str): Combined unique identifier (platform:name)

    Example:
        >>> platform = Platform(identifier="binance")
        >>> owner = OwnerIdentifier(name="trader1", platform=platform)
        >>> print(owner.identifier)  # Outputs: binance:trader1
        >>> owners = {owner}  # Can be used in sets
    """

    def __init__(self, name: str, platform: Platform):
        """Initialize a new owner identifier.

        Args:
            name: Platform-specific owner name
            platform: The platform this owner belongs to
        """
        self._name = name
        self._platform = platform

    @property
    def name(self) -> str:
        """Get the owner's name.

        Returns:
            str: The platform-specific owner name
        """
        return self._name

    @property
    def platform(self) -> Platform:
        """Get the owner's platform.

        Returns:
            Platform: The platform this owner belongs to
        """
        return self._platform

    @property
    def identifier(self) -> Any:
        """Get the unique identifier string.

        The identifier combines the platform identifier and owner name
        in the format "platform:name".

        Returns:
            str: The combined unique identifier
        """
        return f"{self.platform.identifier}:{self.name}"

    def __eq__(self, other: Any) -> bool:
        """Compare this owner identifier with another for equality.

        Args:
            other: The object to compare with

        Returns:
            bool: True if the other object is an OwnerIdentifier with the
                    same platform and identifier
        """
        return (
            isinstance(other, OwnerIdentifier)
            and self.platform == other.platform
            and self.identifier == other.identifier
        )

    def __hash__(self) -> int:
        """Get the hash value of the owner identifier.

        The hash is based on the platform and identifier to ensure
        consistency with equality comparison.

        Returns:
            int: Hash value of the owner identifier
        """
        return hash((self.platform, self.identifier))

    def __repr__(self) -> str:
        """Get the string representation of the owner identifier.

        Returns:
            str: A human-readable representation of the owner
        """
        return f"<Owner: {self.identifier}>"
