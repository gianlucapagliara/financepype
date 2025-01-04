from abc import abstractmethod
from typing import Any

from pydantic import BaseModel, Field, SecretStr


class SubaccountSecrets(BaseModel):
    subaccount_name: str
    api_key: SecretStr
    api_secret: SecretStr
    api_passphrase: SecretStr | None


class ExchangeSecrets(BaseModel):
    name: str
    subaccounts: dict[str, SubaccountSecrets] = Field(default_factory=dict)

    def get_subaccount(self, subaccount_name: str) -> SubaccountSecrets:
        if subaccount_name not in self.subaccounts:
            raise ValueError(f"Subaccount {subaccount_name} not found")
        return self.subaccounts[subaccount_name]

    def add_subaccount(self, subaccount: SubaccountSecrets) -> None:
        self.subaccounts[subaccount.subaccount_name] = subaccount

    def remove_subaccount(self, subaccount_name: str) -> None:
        if subaccount_name not in self.subaccounts:
            raise ValueError(f"Subaccount {subaccount_name} not found")
        del self.subaccounts[subaccount_name]


class ExchangesSecrets(BaseModel):
    secrets: dict[str, ExchangeSecrets] = Field(default_factory=dict)

    def update_secret(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
        if exchange_name not in self.secrets:
            self.secrets[exchange_name] = self.retrieve_secrets(exchange_name, **kwargs)

        return self.secrets[exchange_name]

    def update_secrets(self, exchange_names: list[str], **kwargs: Any) -> None:
        for exchange_name in exchange_names:
            self.update_secret(exchange_name, **kwargs)

    def get_secret(self, exchange_name: str) -> ExchangeSecrets:
        return self.secrets[exchange_name]

    def remove_secret(self, exchange_name: str) -> None:
        if exchange_name not in self.secrets:
            raise ValueError(f"Exchange {exchange_name} not found")
        del self.secrets[exchange_name]

    @abstractmethod
    def retrieve_secrets(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
        raise NotImplementedError("This method should be implemented by the subclass")
