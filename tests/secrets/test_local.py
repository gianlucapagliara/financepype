import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from financepype.secrets.base import ExchangeSecrets, SubaccountSecrets
from financepype.secrets.local import LocalExchangeSecrets


@pytest.fixture
def mock_secrets_data() -> dict[str, Any]:
    return {
        "exchange_secrets": {
            "test_exchange": {
                "name": "test_exchange",
                "subaccounts": {
                    "test_subaccount": {
                        "subaccount_name": "test_subaccount",
                        "api_key": "test_key",
                        "api_secret": "test_secret",
                        "api_passphrase": "test_passphrase",
                    }
                },
            }
        }
    }


@pytest.fixture
def mock_secrets_file(mock_secrets_data: dict[str, Any], tmp_path: Path) -> Path:
    secrets_file = tmp_path / "secrets.json"
    with open(secrets_file, "w") as f:
        json.dump(mock_secrets_data, f)
    return secrets_file


@pytest.fixture
def local_secrets(mock_secrets_file: Path) -> LocalExchangeSecrets:
    return LocalExchangeSecrets(file_path=str(mock_secrets_file))


def test_local_secrets_initialization(
    local_secrets: LocalExchangeSecrets, mock_secrets_file: Path
) -> None:
    """Test that local secrets are properly initialized."""
    assert local_secrets.file_path == str(mock_secrets_file)


def test_get_local_secrets_file_not_found() -> None:
    """Test that get_local_secrets raises FileNotFoundError when file doesn't exist."""
    local_secrets = LocalExchangeSecrets(file_path="nonexistent.json")
    with pytest.raises(FileNotFoundError, match="File nonexistent.json not found"):
        local_secrets.get_local_secrets()


def test_get_local_secrets(
    local_secrets: LocalExchangeSecrets, mock_secrets_data: dict[str, Any]
) -> None:
    """Test that get_local_secrets returns the correct data."""
    secrets = local_secrets.get_local_secrets()
    assert secrets == mock_secrets_data


def test_retrieve_secrets(local_secrets: LocalExchangeSecrets) -> None:
    """Test that retrieve_secrets returns the correct ExchangeSecrets object."""
    secrets = local_secrets.retrieve_secrets("test_exchange")
    assert isinstance(secrets, ExchangeSecrets)
    assert secrets.name == "test_exchange"
    assert len(secrets.subaccounts) == 1

    subaccount = secrets.subaccounts["test_subaccount"]
    assert isinstance(subaccount, SubaccountSecrets)
    assert subaccount.subaccount_name == "test_subaccount"
    assert isinstance(subaccount.api_key, SecretStr)
    assert isinstance(subaccount.api_secret, SecretStr)
    assert isinstance(subaccount.api_passphrase, SecretStr)
    assert subaccount.api_key.get_secret_value() == "test_key"
    assert subaccount.api_secret.get_secret_value() == "test_secret"
    assert subaccount.api_passphrase.get_secret_value() == "test_passphrase"


def test_retrieve_secrets_exchange_not_found(
    local_secrets: LocalExchangeSecrets,
) -> None:
    """Test that retrieve_secrets raises KeyError when exchange is not found."""
    with pytest.raises(KeyError, match="'nonexistent'"):
        local_secrets.retrieve_secrets("nonexistent")
