import json
import os
from typing import Any

from pydantic import BaseModel

from financepype.secrets.base import ExchangeSecrets, ExchangesSecrets


class LocalExchangeSecrets(ExchangesSecrets):
    """Manages exchange secrets stored in a local JSON file.

    This class provides functionality to retrieve and manage exchange credentials
    stored in a local JSON file. It's primarily intended for development and
    testing purposes, not for production use.

    Attributes:
        file_path (str): Path to the JSON file containing the secrets
    """

    file_path: str

    class LocalFormatter(BaseModel):
        """Formats local JSON file data into ExchangeSecrets objects.

        This internal class handles the parsing and validation of JSON data
        from the local file, ensuring it matches the expected format.

        Attributes:
            exchange_secrets (dict[str, ExchangeSecrets]): Map of exchange names to their credentials
        """

        exchange_secrets: dict[str, ExchangeSecrets]

    def retrieve_secrets(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
        """Retrieve and format secrets from the local file.

        Args:
            exchange_name (str): Name of the exchange
            **kwargs: Additional arguments (unused)

        Returns:
            ExchangeSecrets: The formatted exchange credentials

        Raises:
            KeyError: If the exchange is not found in the file
            FileNotFoundError: If the secrets file doesn't exist
        """
        secrets = self.LocalFormatter.model_validate(self.get_local_secrets())
        return secrets.exchange_secrets[exchange_name]

    def get_local_secrets(self) -> dict[str, dict[str, Any]]:
        """Read and parse the local secrets file.

        Returns:
            dict: The parsed JSON data from the file

        Raises:
            FileNotFoundError: If the secrets file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File {self.file_path} not found")

        with open(self.file_path) as file:
            secrets: dict[str, dict[str, Any]] = json.load(file)
        return secrets
