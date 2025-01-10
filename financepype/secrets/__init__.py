"""Secure management of exchange API credentials.

This package provides a secure and flexible system for managing exchange API
credentials across different storage backends. It supports multiple exchanges
and subaccounts, with implementations for both cloud-based (AWS Secrets Manager)
and local storage.

Key Features:
- Secure storage of API keys, secrets, and passphrases
- Support for multiple exchanges and subaccounts
- Pluggable storage backend system
- Built-in AWS Secrets Manager integration
- Local file storage for development/testing

The package includes three main storage implementations:

1. Base System (base.py):
   - Core models and interfaces
   - Secure credential storage
   - Subaccount management

2. AWS Integration (aws.py):
   - AWS Secrets Manager backend
   - Structured JSON secret format
   - AWS profile support

3. Local Storage (local.py):
   - Local JSON file backend
   - Development and testing support
   - Simple file-based storage

Example:
    >>> # Using AWS Secrets Manager
    >>> from financepype.secrets.aws import AWSExchangeSecrets
    >>> secrets = AWSExchangeSecrets(
    ...     profile_name="default",
    ...     secret_names={"binance": "binance/api-keys"}
    ... )
    >>> binance_keys = secrets.get_secret("binance")

    >>> # Using local storage
    >>> from financepype.secrets.local import LocalExchangeSecrets
    >>> local_secrets = LocalExchangeSecrets(file_path="secrets.json")
    >>> kraken_keys = local_secrets.get_secret("kraken")

Security Notes:
1. API credentials are stored using Pydantic's SecretStr to prevent accidental exposure
2. AWS Secrets Manager provides encryption at rest and access control
3. Local storage should only be used for development/testing
4. Proper AWS IAM permissions are required for AWS Secrets Manager access
"""

from financepype.secrets.aws import AWSExchangeSecrets
from financepype.secrets.base import (
    ExchangeSecrets,
    ExchangesSecrets,
    SubaccountSecrets,
)
from financepype.secrets.local import LocalExchangeSecrets

__all__ = [
    "AWSExchangeSecrets",
    "ExchangeSecrets",
    "ExchangesSecrets",
    "LocalExchangeSecrets",
    "SubaccountSecrets",
]
