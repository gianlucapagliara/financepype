from abc import abstractmethod
from typing import Any

from pydantic import BaseModel, Field, SecretStr


class SubaccountSecrets(BaseModel):
    """Represents API credentials for a specific exchange subaccount.

    This class encapsulates the API credentials required to interact with a specific
    subaccount on an exchange. All sensitive data is stored using SecretStr for
    enhanced security.

    Attributes:
        subaccount_name (str): Name of the subaccount
        api_key (SecretStr): API key for authentication
        api_secret (SecretStr): API secret for request signing
        api_passphrase (SecretStr | None): Optional API passphrase (required by some exchanges)
    """

    subaccount_name: str
    api_key: SecretStr
    api_secret: SecretStr
    api_passphrase: SecretStr | None = None


class ExchangeSecrets(BaseModel):
    """Manages API credentials for multiple subaccounts on a single exchange.

    This class provides methods to manage (add, remove, retrieve) subaccount credentials
    for a specific exchange.

    Attributes:
        name (str): Name of the exchange
        subaccounts (dict[str, SubaccountSecrets]): Map of subaccount names to their credentials
    """

    name: str
    subaccounts: dict[str, SubaccountSecrets] = Field(default_factory=dict)

    def get_subaccount(self, subaccount_name: str) -> SubaccountSecrets:
        """Retrieve credentials for a specific subaccount.

        Args:
            subaccount_name (str): Name of the subaccount to retrieve

        Returns:
            SubaccountSecrets: The subaccount credentials

        Raises:
            ValueError: If the subaccount is not found
        """
        if subaccount_name not in self.subaccounts:
            raise ValueError(f"Subaccount {subaccount_name} not found")
        return self.subaccounts[subaccount_name]

    def add_subaccount(self, subaccount: SubaccountSecrets) -> None:
        """Add or update credentials for a subaccount.

        Args:
            subaccount (SubaccountSecrets): The subaccount credentials to add/update
        """
        self.subaccounts[subaccount.subaccount_name] = subaccount

    def remove_subaccount(self, subaccount_name: str) -> None:
        """Remove credentials for a specific subaccount.

        Args:
            subaccount_name (str): Name of the subaccount to remove

        Raises:
            ValueError: If the subaccount is not found
        """
        if subaccount_name not in self.subaccounts:
            raise ValueError(f"Subaccount {subaccount_name} not found")
        del self.subaccounts[subaccount_name]


class ExchangesSecrets(BaseModel):
    """Abstract base class for managing exchange secrets across different storage backends.

    This class provides a common interface for retrieving and managing exchange credentials,
    regardless of where they are stored (e.g., AWS Secrets Manager, local file).

    Attributes:
        secrets (dict[str, ExchangeSecrets]): Cache of retrieved exchange credentials
    """

    secrets: dict[str, ExchangeSecrets] = Field(default_factory=dict)

    def update_secret(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
        """Update or retrieve credentials for a specific exchange.

        Args:
            exchange_name (str): Name of the exchange
            **kwargs: Additional arguments passed to retrieve_secrets

        Returns:
            ExchangeSecrets: The exchange credentials
        """
        if exchange_name not in self.secrets:
            self.secrets[exchange_name] = self.retrieve_secrets(exchange_name, **kwargs)

        return self.secrets[exchange_name]

    def update_secrets(self, exchange_names: list[str], **kwargs: Any) -> None:
        """Update or retrieve credentials for multiple exchanges.

        Args:
            exchange_names (list[str]): List of exchange names
            **kwargs: Additional arguments passed to retrieve_secrets
        """
        for exchange_name in exchange_names:
            self.update_secret(exchange_name, **kwargs)

    def get_secret(self, exchange_name: str) -> ExchangeSecrets:
        """Get cached credentials for a specific exchange.

        Args:
            exchange_name (str): Name of the exchange

        Returns:
            ExchangeSecrets: The exchange credentials

        Raises:
            KeyError: If the exchange credentials are not in the cache
        """
        return self.secrets[exchange_name]

    def remove_secret(self, exchange_name: str) -> None:
        """Remove cached credentials for a specific exchange.

        Args:
            exchange_name (str): Name of the exchange to remove

        Raises:
            ValueError: If the exchange is not found in the cache
        """
        if exchange_name not in self.secrets:
            raise ValueError(f"Exchange {exchange_name} not found")
        del self.secrets[exchange_name]

    @abstractmethod
    def retrieve_secrets(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
        """Retrieve credentials from the storage backend.

        This method must be implemented by subclasses to define how to retrieve
        credentials from their specific storage backend.

        Args:
            exchange_name (str): Name of the exchange
            **kwargs: Implementation-specific arguments

        Returns:
            ExchangeSecrets: The retrieved exchange credentials

        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError("This method should be implemented by the subclass")
