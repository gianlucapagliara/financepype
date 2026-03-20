# API Reference — Platforms

## financepype.platforms.platform

### Platform

```
class Platform(BaseModel)  [frozen]
```

Immutable, globally-cached trading venue identifier.

**Fields**

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| `identifier` | `str` | `min_length=1` | Unique platform name |

**Constructor**

```python
Platform(identifier: str)
```

Uses `__new__` to return a cached instance when the same identifier is requested. Cache key: `"Platform:{identifier}"`.

**Methods**

| Method | Description |
|--------|-------------|
| `clear_cache() [classmethod]` | Remove all cached instances |

**Special Methods**

- `__str__` → `self.identifier`
- `__repr__` → `"<Platform: {identifier}>"`

---

## financepype.platforms.centralized

### CentralizedPlatform

```
class CentralizedPlatform(Platform)
```

Extends `Platform` for centralised exchanges.

**Additional Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sub_identifier` | `str \| None` | `None` | Sub-account or trading mode ID |
| `domain` | `str \| None` | `None` | Exchange domain |

Cache key includes `sub_identifier` when present, so `CentralizedPlatform(identifier="okx", sub_identifier="demo")` and `CentralizedPlatform(identifier="okx")` are different instances.

---

## financepype.platforms.blockchain

### BlockchainType

```
class BlockchainType(Enum)
```

An empty enum — extend it in your project to define supported chain types:

```python
from enum import Enum
from financepype.platforms.blockchain import BlockchainType

class ChainType(BlockchainType):
    EVM = "EVM"
    SOLANA = "SOLANA"
```

### BlockchainPlatform

```
class BlockchainPlatform(Platform)
```

Extends `Platform` for blockchain networks.

**Additional Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `BlockchainType` | required | Blockchain ecosystem |
| `local` | `bool` | `False` | Local dev node |
| `testnet` | `bool` | `False` | Test network |
| `chain_id` | `int \| str \| None` | `None` | EVM chain ID or equivalent |

**Caching**

The cache key includes `type`, `local`, `testnet`, and `chain_id`, so different network configurations of the same base identifier are separate instances.
