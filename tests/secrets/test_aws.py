import json
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from financepype.secrets.aws import AWSExchangeSecrets
from financepype.secrets.base import ExchangeSecrets, SubaccountSecrets


@pytest.fixture
def mock_aws_secrets_data() -> dict[str, Any]:
    return {
        "name": "test_exchange",
        "API_KEY": "test_key",
        "API_SECRET": "test_secret",
        "API_PASSPHRASE": "test_passphrase",
        "SUBACCOUNTS": [
            {
                "subaccount_name": "test_subaccount",
                "API_KEY": "test_subaccount_key",
                "API_SECRET": "test_subaccount_secret",
                "API_PASSPHRASE": "test_subaccount_passphrase",
            }
        ],
    }


@pytest.fixture
def mock_aws_client() -> Generator[MagicMock, None, None]:
    with patch("boto3.session.Session") as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.region_name = "us-east-1"
        yield mock_client


@pytest.fixture
def aws_secrets(mock_aws_client: MagicMock) -> AWSExchangeSecrets:
    return AWSExchangeSecrets(
        profile_name="test_profile",
        secret_names={"test_exchange": "test_secret_name"},
    )


def test_aws_secrets_initialization(aws_secrets: AWSExchangeSecrets) -> None:
    """Test that AWS secrets are properly initialized."""
    assert aws_secrets.profile_name == "test_profile"
    assert aws_secrets.secret_names == {"test_exchange": "test_secret_name"}


def test_get_aws_secret(
    aws_secrets: AWSExchangeSecrets,
    mock_aws_client: MagicMock,
    mock_aws_secrets_data: dict[str, Any],
) -> None:
    """Test getting a secret from AWS Secrets Manager."""
    mock_aws_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_aws_secrets_data)
    }

    secret = aws_secrets.get_aws_secret("test_secret_name")
    assert secret == mock_aws_secrets_data

    mock_aws_client.get_secret_value.assert_called_once_with(
        SecretId="test_secret_name"
    )


def test_get_aws_secret_invalid_json(
    aws_secrets: AWSExchangeSecrets, mock_aws_client: MagicMock
) -> None:
    """Test that getting a non-JSON secret raises ValueError."""
    mock_aws_client.get_secret_value.return_value = {"SecretBinary": b"not json"}

    with pytest.raises(ValueError, match="Secret is not a valid JSON string"):
        aws_secrets.get_aws_secret("test_secret_name")


def test_retrieve_secrets(
    aws_secrets: AWSExchangeSecrets,
    mock_aws_client: MagicMock,
    mock_aws_secrets_data: dict[str, Any],
) -> None:
    """Test retrieving secrets for an exchange."""
    mock_aws_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_aws_secrets_data)
    }

    secrets = aws_secrets.retrieve_secrets("test_exchange")
    assert isinstance(secrets, ExchangeSecrets)
    assert secrets.name == "test_exchange"
    assert len(secrets.subaccounts) == 1

    subaccount = secrets.subaccounts["test_subaccount"]
    assert isinstance(subaccount, SubaccountSecrets)
    assert subaccount.subaccount_name == "test_subaccount"
    assert isinstance(subaccount.api_key, SecretStr)
    assert isinstance(subaccount.api_secret, SecretStr)
    assert isinstance(subaccount.api_passphrase, SecretStr)
    assert subaccount.api_key.get_secret_value() == "test_subaccount_key"
    assert subaccount.api_secret.get_secret_value() == "test_subaccount_secret"
    assert subaccount.api_passphrase.get_secret_value() == "test_subaccount_passphrase"


def test_retrieve_secrets_exchange_not_found(
    aws_secrets: AWSExchangeSecrets,
) -> None:
    """Test that retrieving secrets for a non-existent exchange raises ValueError."""
    with pytest.raises(ValueError, match="No secrets set for nonexistent"):
        aws_secrets.retrieve_secrets("nonexistent")


def test_retrieve_secrets_aws_error(
    aws_secrets: AWSExchangeSecrets, mock_aws_client: MagicMock
) -> None:
    """Test that AWS errors are properly handled."""
    mock_aws_client.get_secret_value.side_effect = Exception("AWS error")

    with pytest.raises(ValueError, match="No secrets found for test_exchange"):
        aws_secrets.retrieve_secrets("test_exchange")
