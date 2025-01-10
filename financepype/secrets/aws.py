import json
from typing import Any

import boto3
import boto3.session
from pydantic import BaseModel, Field, SecretStr

from financepype.secrets.base import (
    ExchangeSecrets,
    ExchangesSecrets,
    SubaccountSecrets,
)


class AWSExchangeSecrets(ExchangesSecrets):
    """Manages exchange secrets stored in AWS Secrets Manager.

    This class provides functionality to retrieve and manage exchange credentials
    stored in AWS Secrets Manager. It supports a specific JSON format for storing
    credentials and handles multiple subaccounts per exchange.

    Attributes:
        profile_name (str | None): AWS profile name to use for authentication
        secret_names (dict[str, str]): Mapping of exchange names to their AWS secret names
    """

    profile_name: str | None
    secret_names: dict[str, str]

    class SecretsFormatter(BaseModel):
        """Formats AWS Secrets Manager JSON data into ExchangeSecrets objects.

        This internal class handles the parsing and validation of JSON data retrieved
        from AWS Secrets Manager, ensuring it matches the expected format.

        Attributes:
            name (str): Exchange name
            API_KEY (str): Main API key
            API_SECRET (str): Main API secret
            API_PASSPHRASE (str | None): Optional API passphrase
            SUBACCOUNTS (list[SubaccountFormat]): List of subaccount configurations
        """

        name: str
        API_KEY: str
        API_SECRET: str
        API_PASSPHRASE: str | None = None

        class SubaccountFormat(BaseModel):
            """Format for subaccount credentials within AWS Secrets.

            Attributes:
                subaccount_name (str): Name of the subaccount
                API_KEY (str): Subaccount API key
                API_SECRET (str): Subaccount API secret
                API_PASSPHRASE (str | None): Optional subaccount API passphrase
            """

            subaccount_name: str
            API_KEY: str
            API_SECRET: str
            API_PASSPHRASE: str | None = None

            def get_subaccount_secrets(self) -> SubaccountSecrets:
                """Convert AWS secret format to SubaccountSecrets.

                Returns:
                    SubaccountSecrets: Formatted subaccount credentials
                """
                return SubaccountSecrets(
                    subaccount_name=self.subaccount_name,
                    api_key=SecretStr(self.API_KEY),
                    api_secret=SecretStr(self.API_SECRET),
                    api_passphrase=(
                        SecretStr(self.API_PASSPHRASE)
                        if self.API_PASSPHRASE is not None
                        else None
                    ),
                )

        SUBACCOUNTS: list[SubaccountFormat] = Field(
            default_factory=list, description="List of subaccount configurations"
        )

        def get_secrets(self) -> ExchangeSecrets:
            """Convert AWS secret format to ExchangeSecrets.

            Returns:
                ExchangeSecrets: Formatted exchange credentials with all subaccounts
            """
            exchange_secrets = ExchangeSecrets(name=self.name)
            for subaccount in self.SUBACCOUNTS:
                exchange_secrets.add_subaccount(subaccount.get_subaccount_secrets())
            return exchange_secrets

    def retrieve_secrets(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
        """Retrieve and format secrets from AWS Secrets Manager.

        Args:
            exchange_name (str): Name of the exchange
            **kwargs: Additional arguments (unused)

        Returns:
            ExchangeSecrets: The formatted exchange credentials

        Raises:
            ValueError: If secrets are not found or invalid
        """
        if exchange_name not in self.secret_names:
            raise ValueError(f"No secrets set for {exchange_name}")

        try:
            dict_secrets: dict[str, Any] = self.get_aws_secret(
                self.secret_names[exchange_name]
            )
            dict_secrets["name"] = exchange_name
        except Exception as e:
            raise ValueError(f"No secrets found for {exchange_name}") from e

        exchange_secrets = self.SecretsFormatter.model_validate(dict_secrets)
        return exchange_secrets.get_secrets()

    def get_aws_secret(
        self, secret_name: str
    ) -> dict[str, dict[str, Any] | str | list[dict[str, Any]]]:
        """Retrieve a secret from AWS Secrets Manager.

        Args:
            secret_name (str): Name of the secret in AWS Secrets Manager

        Returns:
            dict: The parsed JSON secret data

        Raises:
            ValueError: If the secret is not a valid JSON string
        """
        session = boto3.session.Session(profile_name=self.profile_name)
        client = session.client(
            service_name="secretsmanager", region_name=session.region_name
        )

        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in get_secret_value_response:
            secret_str: str = get_secret_value_response["SecretString"]
            secret: dict[str, dict[str, Any] | str | list[dict[str, Any]]] = json.loads(
                secret_str
            )
        else:
            raise ValueError("Secret is not a valid JSON string")

        return secret
