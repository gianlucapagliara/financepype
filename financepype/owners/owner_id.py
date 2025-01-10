from pydantic import BaseModel, ConfigDict

from financepype.platforms.platform import Platform


class OwnerIdentifier(BaseModel):
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

    model_config = ConfigDict(frozen=True)

    name: str
    platform: Platform

    @property
    def identifier(self) -> str:
        """Get the unique identifier string.

        The identifier combines the platform identifier and owner name
        in the format "platform:name".

        Returns:
            str: The combined unique identifier
        """
        return f"{self.platform.identifier}:{self.name}"

    def __repr__(self) -> str:
        """Get the string representation of the owner identifier.

        Returns:
            str: A human-readable representation of the owner
        """
        return f"<Owner: {self.identifier}>"
