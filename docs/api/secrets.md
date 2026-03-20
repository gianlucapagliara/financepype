# API Reference — Secrets

## financepype.secrets.base

### SubaccountSecrets

```
class SubaccountSecrets(BaseModel)
```

API credentials for a single exchange sub-account.

| Field | Type | Description |
|-------|------|-------------|
| `subaccount_name` | `str` | Sub-account identifier |
| `api_key` | `SecretStr` | API key |
| `api_secret` | `SecretStr` | API secret |
| `api_passphrase` | `SecretStr \| None` | Optional passphrase |

`SecretStr` redacts values in `repr()` and logs. Use `.get_secret_value()` to access the underlying string.

---

### ExchangeSecrets

```
class ExchangeSecrets(BaseModel)
```

Credentials for all sub-accounts on one exchange.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Exchange name |
| `subaccounts` | `dict[str, SubaccountSecrets]` | Keyed by sub-account name |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_subaccount` | `(name: str) -> SubaccountSecrets` | Retrieve; raises `ValueError` if missing |
| `add_subaccount` | `(sub: SubaccountSecrets) -> None` | Add or overwrite |
| `remove_subaccount` | `(name: str) -> None` | Remove; raises `ValueError` if missing |

---

### ExchangesSecrets

```
class ExchangesSecrets(BaseModel) [abstract]
```

Abstract base for multi-exchange credential stores. Provides in-memory caching of retrieved secrets.

| Field | Type | Description |
|-------|------|-------------|
| `secrets` | `dict[str, ExchangeSecrets]` | Cache of retrieved credentials |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `update_secret` | `(name: str, **kwargs) -> ExchangeSecrets` | Load into cache if not present |
| `update_secrets` | `(names: list[str], **kwargs) -> None` | Load multiple |
| `get_secret` | `(name: str) -> ExchangeSecrets` | Read from cache |
| `remove_secret` | `(name: str) -> None` | Remove from cache |
| `retrieve_secrets` | `(name: str, **kwargs) -> ExchangeSecrets` [abstract] | Fetch from backend |

---

## financepype.secrets.local

### LocalExchangeSecrets

```
class LocalExchangeSecrets(ExchangesSecrets)
```

Reads credentials from a local JSON file.

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | `str` | Path to the JSON file |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `retrieve_secrets` | `(name: str, **kwargs) -> ExchangeSecrets` | Parse JSON and return credentials |
| `get_local_secrets` | `() -> dict` | Read and parse the raw JSON |

**Expected JSON structure**

```json
{
  "exchange_secrets": {
    "<exchange_name>": {
      "name": "<exchange_name>",
      "subaccounts": {
        "<sub_name>": {
          "subaccount_name": "<sub_name>",
          "api_key": "...",
          "api_secret": "...",
          "api_passphrase": null
        }
      }
    }
  }
}
```

**Raises**

- `FileNotFoundError` — file does not exist
- `KeyError` — exchange not in file

---

## financepype.secrets.aws

### AWSExchangeSecrets

```
class AWSExchangeSecrets(ExchangesSecrets)
```

Reads credentials from AWS Secrets Manager.

| Field | Type | Description |
|-------|------|-------------|
| `profile_name` | `str \| None` | AWS named profile; `None` = default credentials chain |
| `secret_names` | `dict[str, str]` | Maps exchange name → AWS secret name |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `retrieve_secrets` | `(name: str, **kwargs) -> ExchangeSecrets` | Fetch from Secrets Manager |
| `get_aws_secret` | `(secret_name: str) -> dict` | Raw AWS API call |

**Inner Classes**

#### AWSExchangeSecrets.SecretsFormatter

Parses the AWS secret JSON:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Exchange name |
| `API_KEY` | `str` | Main API key |
| `API_SECRET` | `str` | Main API secret |
| `API_PASSPHRASE` | `str \| None` | Optional |
| `SUBACCOUNTS` | `list[SubaccountFormat]` | Sub-account list |

#### AWSExchangeSecrets.SecretsFormatter.SubaccountFormat

| Field | Type |
|-------|------|
| `subaccount_name` | `str` |
| `API_KEY` | `str` |
| `API_SECRET` | `str` |
| `API_PASSPHRASE` | `str \| None` |

**`retrieve_secrets` raises**

- `ValueError` — exchange not in `secret_names` or secret not found / invalid JSON

**AWS Secret JSON Format**

```json
{
  "name": "binance",
  "API_KEY": "main_key",
  "API_SECRET": "main_secret",
  "API_PASSPHRASE": null,
  "SUBACCOUNTS": [
    {
      "subaccount_name": "sub1",
      "API_KEY": "sub1_key",
      "API_SECRET": "sub1_secret",
      "API_PASSPHRASE": null
    }
  ]
}
```
