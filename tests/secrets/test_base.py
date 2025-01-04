from typing import Any

import pytest
from pydantic import SecretStr

from financepype.secrets.base import (
    ExchangeSecrets,
    ExchangesSecrets,
    SubaccountSecrets,
)


class TestExchangesSecrets(ExchangesSecrets):
    """Test implementation of ExchangesSecrets."""

    def retrieve_secrets(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
        """Test implementation of retrieve_secrets."""
        return ExchangeSecrets(
            name=exchange_name,
            subaccounts={
                "main": SubaccountSecrets(
                    subaccount_name="main",
                    api_key=SecretStr("test_key"),
                    api_secret=SecretStr("test_secret"),
                    api_passphrase=SecretStr("test_pass"),
                )
            },
        )


@pytest.fixture
def subaccount_secrets() -> SubaccountSecrets:
    return SubaccountSecrets(
        subaccount_name="test_account",
        api_key=SecretStr("test_key"),
        api_secret=SecretStr("test_secret"),
        api_passphrase=SecretStr("test_pass"),
    )


@pytest.fixture
def exchange_secrets(subaccount_secrets: SubaccountSecrets) -> ExchangeSecrets:
    return ExchangeSecrets(
        name="test_exchange",
        subaccounts={"test_account": subaccount_secrets},
    )


@pytest.fixture
def exchanges_secrets() -> ExchangesSecrets:
    return TestExchangesSecrets()


def test_subaccount_secrets_initialization(
    subaccount_secrets: SubaccountSecrets,
) -> None:
    """Test that subaccount secrets are properly initialized."""
    assert subaccount_secrets.subaccount_name == "test_account"
    assert subaccount_secrets.api_key.get_secret_value() == "test_key"
    assert subaccount_secrets.api_secret.get_secret_value() == "test_secret"
    assert subaccount_secrets.api_passphrase is not None
    assert subaccount_secrets.api_passphrase.get_secret_value() == "test_pass"


def test_subaccount_secrets_without_passphrase() -> None:
    """Test that subaccount secrets can be created without a passphrase."""
    subaccount = SubaccountSecrets(
        subaccount_name="test_account",
        api_key=SecretStr("test_key"),
        api_secret=SecretStr("test_secret"),
        api_passphrase=None,
    )
    assert subaccount.api_passphrase is None


def test_exchange_secrets_initialization(
    exchange_secrets: ExchangeSecrets, subaccount_secrets: SubaccountSecrets
) -> None:
    """Test that exchange secrets are properly initialized."""
    assert exchange_secrets.name == "test_exchange"
    assert exchange_secrets.subaccounts["test_account"] == subaccount_secrets


def test_exchange_secrets_get_subaccount(
    exchange_secrets: ExchangeSecrets, subaccount_secrets: SubaccountSecrets
) -> None:
    """Test getting a subaccount from exchange secrets."""
    assert exchange_secrets.get_subaccount("test_account") == subaccount_secrets
    with pytest.raises(ValueError):
        exchange_secrets.get_subaccount("nonexistent")


def test_exchange_secrets_add_subaccount(exchange_secrets: ExchangeSecrets) -> None:
    """Test adding a subaccount to exchange secrets."""
    new_subaccount = SubaccountSecrets(
        subaccount_name="new_account",
        api_key=SecretStr("new_key"),
        api_secret=SecretStr("new_secret"),
        api_passphrase=SecretStr("new_pass"),
    )
    exchange_secrets.add_subaccount(new_subaccount)
    assert exchange_secrets.subaccounts["new_account"] == new_subaccount


def test_exchange_secrets_remove_subaccount(exchange_secrets: ExchangeSecrets) -> None:
    """Test removing a subaccount from exchange secrets."""
    exchange_secrets.remove_subaccount("test_account")
    assert "test_account" not in exchange_secrets.subaccounts
    with pytest.raises(ValueError):
        exchange_secrets.remove_subaccount("nonexistent")


def test_exchanges_secrets_initialization(exchanges_secrets: ExchangesSecrets) -> None:
    """Test that exchanges secrets are properly initialized."""
    assert exchanges_secrets.secrets == {}


def test_exchanges_secrets_update_secret(exchanges_secrets: ExchangesSecrets) -> None:
    """Test updating a secret in exchanges secrets."""
    secret = exchanges_secrets.update_secret("test_exchange")
    assert secret.name == "test_exchange"
    assert "main" in secret.subaccounts


def test_exchanges_secrets_update_secrets(exchanges_secrets: ExchangesSecrets) -> None:
    """Test updating multiple secrets in exchanges secrets."""
    exchanges_secrets.update_secrets(["test_exchange1", "test_exchange2"])
    assert "test_exchange1" in exchanges_secrets.secrets
    assert "test_exchange2" in exchanges_secrets.secrets


def test_exchanges_secrets_get_secret(exchanges_secrets: ExchangesSecrets) -> None:
    """Test getting a secret from exchanges secrets."""
    exchanges_secrets.update_secret("test_exchange")
    secret = exchanges_secrets.get_secret("test_exchange")
    assert secret.name == "test_exchange"
    with pytest.raises(KeyError):
        exchanges_secrets.get_secret("nonexistent")


def test_exchanges_secrets_remove_secret(exchanges_secrets: ExchangesSecrets) -> None:
    """Test removing a secret from exchanges secrets."""
    exchanges_secrets.update_secret("test_exchange")
    exchanges_secrets.remove_secret("test_exchange")
    assert "test_exchange" not in exchanges_secrets.secrets
    with pytest.raises(ValueError):
        exchanges_secrets.remove_secret("nonexistent")
