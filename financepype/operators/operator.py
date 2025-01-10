from pydantic import BaseModel

from financepype.constants import get_instance_id
from financepype.operators.nonce_creator import NonceCreator
from financepype.platforms.platform import Platform


class OperatorConfiguration(BaseModel):
    platform: Platform


class Operator:
    """Base class for platform operators.

    An operator represents a connection to a trading platform or blockchain,
    providing a standardized interface for interacting with different platforms.
    Each operator maintains its own platform-specific state and identifiers.

    Attributes:
        _platform (Platform): The platform this operator connects to
        _microseconds_nonce_provider (NonceCreator): Generator for unique operation IDs
        _client_instance_id (str): Unique identifier for this client instance

    Example:
        >>> platform = Platform("binance")
        >>> operator = Operator(platform)
        >>> print(operator.name)  # Output: "binance"
    """

    def __init__(self, configuration: OperatorConfiguration):
        """Initialize a new operator.

        Args:
            configuration (OperatorConfiguration): The configuration for the operator
        """
        super().__init__()

        self._configuration = configuration

        self._microseconds_nonce_provider = NonceCreator.for_microseconds()
        self._client_instance_id = get_instance_id()

    @property
    def platform(self) -> object:
        """Get the platform this operator connects to.

        Returns:
            object: The platform instance
        """
        return self._configuration.platform

    @property
    def name(self) -> str:
        """Get the name of this operator.

        Returns:
            str: The platform name
        """
        return str(self.platform)

    @property
    def display_name(self) -> str:
        """Get a human-readable name for this operator.

        Returns:
            str: The display name
        """
        return self.name
