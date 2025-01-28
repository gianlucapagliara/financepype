from abc import abstractmethod
from typing import Any, Self

from pydantic import BaseModel, ConfigDict


class BlockchainIdentifier(BaseModel):
    """An immutable identifier for blockchain-related entities.

    This class provides a standardized way to identify blockchain entities within the system.
    The identifier is immutable to ensure consistency and can be safely used as a dictionary key or in sets.

    Example:
        >>> id1 = ConcreteBlockchainIdentifier(raw="0x123", string="0x123")
        >>> id2 = ConcreteBlockchainIdentifier(raw="0x123", string="0x123")
        >>> assert id1 == id2
        >>> identifiers = {id1}  # Can be used in sets
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    raw: Any
    string: str

    @classmethod
    def from_raw(cls, value: Any) -> Self:
        return cls(raw=value, string=cls.id_to_string(value))

    @classmethod
    def from_string(cls, value: str) -> Self:
        return cls(raw=cls.id_from_string(value), string=value)

    @classmethod
    @abstractmethod
    def is_valid(cls, value: Any) -> bool:
        """Check if a value is valid for this identifier type.

        Args:
            value: The value to validate

        Returns:
            bool: True if the value is valid
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def id_from_string(cls, value: str) -> Any:
        """Convert a string representation to the raw identifier value.

        Args:
            value: The string to convert

        Returns:
            Any: The raw identifier value
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def id_to_string(cls, value: Any) -> str:
        """Convert a raw identifier value to its string representation.

        Args:
            value: The raw value to convert

        Returns:
            str: The string representation
        """
        raise NotImplementedError

    def __str__(self) -> str:
        """Get the string representation of the identifier.

        Returns:
            str: The string representation
        """
        return self.string

    def __repr__(self) -> str:
        """Get the debug representation of the identifier.

        Returns:
            str: The debug representation
        """
        return f"<{self.__class__.__name__}: {self.string}>"

    def __eq__(self, other: object) -> bool:
        """Compare this identifier with another for equality.

        Args:
            other: The object to compare with

        Returns:
            bool: True if the other object is a BlockchainIdentifier with the same string value
        """
        if not isinstance(other, BlockchainIdentifier):
            return False
        return self.string == other.string

    def __hash__(self) -> int:
        """Get the hash value of the identifier.

        The hash is based on the string value to ensure consistency with equality comparison.

        Returns:
            int: Hash value of the identifier
        """
        return hash(self.string)
