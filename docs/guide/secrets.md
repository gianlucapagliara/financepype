# Secrets

The `secrets` module manages API credentials for trading accounts. It supports multiple storage backends and keeps sensitive values out of source code and logs.

## Design

All sensitive string values use Pydantic's `SecretStr`, which redacts values in logs and `repr()` output. The module provides:

- `SubaccountSecrets` — credentials for a single sub-account
- `ExchangeSecrets` — credentials for all sub-accounts on one exchange
- `ExchangesSecrets` — abstract base for multi-exchange credential stores
- `LocalExchangeSecrets` — reads from a local JSON file
- `AWSExchangeSecrets` — reads from AWS Secrets Manager

## Core Models

### SubaccountSecrets

```python
from pydantic import SecretStr
from financepype.secrets.base import SubaccountSecrets

sub = SubaccountSecrets(
    subaccount_name="main",
    api_key=SecretStr("your_api_key"),
    api_secret=SecretStr("your_api_secret"),
    api_passphrase=SecretStr("optional_passphrase"),  # None if not required
)

# SecretStr prevents accidental logging
print(sub.api_key)                      # **********
print(sub.api_key.get_secret_value())   # your_api_key (explicit access)
```

### ExchangeSecrets

```python
from financepype.secrets.base import ExchangeSecrets

exchange = ExchangeSecrets(name="binance")
exchange.add_subaccount(sub)

# Retrieve
main = exchange.get_subaccount("main")

# Remove
exchange.remove_subaccount("main")
```

### ExchangesSecrets (Abstract)

```python
from financepype.secrets.base import ExchangesSecrets

class MySecretStore(ExchangesSecrets):
    def retrieve_secrets(self, exchange_name: str, **kwargs) -> ExchangeSecrets:
        # implement fetching from your backend
        ...
```

Key methods:

```python
store = MySecretStore()

# Load into cache
store.update_secret("binance")        # single
store.update_secrets(["binance", "okx"])  # multiple

# Read from cache
exchange_creds = store.get_secret("binance")

# Remove from cache
store.remove_secret("binance")
```

## Local JSON Backend

`LocalExchangeSecrets` reads credentials from a JSON file. Intended for development and testing — **do not use in production**.

```python
from financepype.secrets.local import LocalExchangeSecrets

store = LocalExchangeSecrets(file_path="/path/to/secrets.json")
creds = store.update_secret("binance")
sub = creds.get_subaccount("main")
print(sub.api_key.get_secret_value())
```

### Expected JSON Format

```json
{
  "exchange_secrets": {
    "binance": {
      "name": "binance",
      "subaccounts": {
        "main": {
          "subaccount_name": "main",
          "api_key": "BINANCE_API_KEY",
          "api_secret": "BINANCE_API_SECRET",
          "api_passphrase": null
        },
        "sub1": {
          "subaccount_name": "sub1",
          "api_key": "SUB1_API_KEY",
          "api_secret": "SUB1_API_SECRET"
        }
      }
    },
    "okx": {
      "name": "okx",
      "subaccounts": {
        "main": {
          "subaccount_name": "main",
          "api_key": "OKX_API_KEY",
          "api_secret": "OKX_API_SECRET",
          "api_passphrase": "OKX_PASSPHRASE"
        }
      }
    }
  }
}
```

!!! warning
    Never commit your secrets file to version control. Add it to `.gitignore`.

## AWS Secrets Manager Backend

`AWSExchangeSecrets` fetches credentials from AWS Secrets Manager. Suitable for production deployments.

```python
from financepype.secrets.aws import AWSExchangeSecrets

store = AWSExchangeSecrets(
    profile_name="my-aws-profile",   # None to use default credentials chain
    secret_names={
        "binance": "prod/trading/binance",
        "okx":     "prod/trading/okx",
    },
)

creds = store.update_secret("binance")
sub = creds.get_subaccount("main")
```

### AWS Secret JSON Format

Each secret in AWS Secrets Manager must be a JSON string with this structure:

```json
{
  "name": "binance",
  "API_KEY": "main_api_key",
  "API_SECRET": "main_api_secret",
  "API_PASSPHRASE": null,
  "SUBACCOUNTS": [
    {
      "subaccount_name": "sub1",
      "API_KEY": "sub1_api_key",
      "API_SECRET": "sub1_api_secret",
      "API_PASSPHRASE": null
    }
  ]
}
```

### AWS Authentication

The library uses `boto3.session.Session(profile_name=...)`. If `profile_name` is `None`, boto3 will use the default credentials chain (environment variables, instance profile, etc.).

```python
# Using environment variables (recommended for containers)
store = AWSExchangeSecrets(
    profile_name=None,  # use AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars
    secret_names={"binance": "prod/binance"},
)

# Using a named profile from ~/.aws/credentials
store = AWSExchangeSecrets(
    profile_name="trading-prod",
    secret_names={"binance": "prod/binance"},
)
```

## Implementing a Custom Backend

Subclass `ExchangesSecrets` and implement `retrieve_secrets`:

```python
from financepype.secrets.base import ExchangeSecrets, ExchangesSecrets, SubaccountSecrets
from pydantic import SecretStr

class VaultSecrets(ExchangesSecrets):
    vault_url: str
    token: SecretStr

    def retrieve_secrets(self, exchange_name: str, **kwargs) -> ExchangeSecrets:
        # Call your Vault API
        data = vault_client.read(f"secret/{exchange_name}")
        exchange = ExchangeSecrets(name=exchange_name)
        for acct in data["subaccounts"]:
            exchange.add_subaccount(SubaccountSecrets(
                subaccount_name=acct["name"],
                api_key=SecretStr(acct["key"]),
                api_secret=SecretStr(acct["secret"]),
            ))
        return exchange
```
