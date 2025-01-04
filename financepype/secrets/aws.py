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
    profile_name: str | None
    secret_names: dict[str, str]

    class SecretsFormatter(BaseModel):
        name: str
        API_KEY: str
        API_SECRET: str
        API_PASSPHRASE: str | None = None

        class SubaccountFormat(BaseModel):
            subaccount_name: str
            API_KEY: str
            API_SECRET: str
            API_PASSPHRASE: str | None = None

            def get_subaccount_secrets(self) -> SubaccountSecrets:
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
            exchange_secrets = ExchangeSecrets(name=self.name)
            for subaccount in self.SUBACCOUNTS:
                exchange_secrets.add_subaccount(subaccount.get_subaccount_secrets())
            return exchange_secrets

    def retrieve_secrets(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
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
