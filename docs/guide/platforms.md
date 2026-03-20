# Platforms

A `Platform` is an immutable, cached identifier for a trading venue. Every asset, owner, and operator is bound to a platform, enabling consistent cross-venue comparisons.

## Platform (Base Class)

```python
from financepype.platforms.platform import Platform

binance = Platform(identifier="binance")
kraken = Platform(identifier="kraken")

print(str(binance))   # binance
print(repr(binance))  # <Platform: binance>
```

### Caching / Singleton Behaviour

Platforms use a global cache keyed on `ClassName:identifier[:key=value...]`. Constructing the same class with the same arguments always returns the same Python object.

```python
p1 = Platform(identifier="binance")
p2 = Platform(identifier="binance")
assert p1 is p2  # True
```

To clear the cache (e.g., in tests):

```python
Platform.clear_cache()
```

### Immutability

`Platform` uses `model_config = ConfigDict(frozen=True)`. Fields cannot be changed after construction.

## CentralizedPlatform

Use `CentralizedPlatform` for centralized exchanges. It adds optional `sub_identifier` (for sub-accounts or paper trading modes) and `domain` (for API base URL tracking).

```python
from financepype.platforms.centralized import CentralizedPlatform

okx = CentralizedPlatform(
    identifier="okx",
    sub_identifier="demo",   # e.g. paper trading account
    domain="www.okx.com",
)

# Sub-identifier is included in the cache key
okx_demo = CentralizedPlatform(identifier="okx", sub_identifier="demo")
okx_live = CentralizedPlatform(identifier="okx", sub_identifier=None)
assert okx_demo is not okx_live
```

## BlockchainPlatform

Use `BlockchainPlatform` for blockchain networks. It adds chain-specific metadata.

```python
from financepype.platforms.blockchain import BlockchainPlatform, BlockchainType

# BlockchainType is an empty enum that you extend in your project
class MyBlockchainType(BlockchainType):
    EVM = "EVM"
    SOLANA = "SOLANA"

ethereum = BlockchainPlatform(
    identifier="ethereum",
    type=MyBlockchainType.EVM,
    chain_id=1,
    local=False,
    testnet=False,
)

sepolia = BlockchainPlatform(
    identifier="sepolia",
    type=MyBlockchainType.EVM,
    chain_id=11155111,
    testnet=True,
)

ganache = BlockchainPlatform(
    identifier="ganache",
    type=MyBlockchainType.EVM,
    local=True,
)
```

### BlockchainPlatform Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `BlockchainType` | required | Blockchain ecosystem |
| `local` | `bool` | `False` | Local dev chain (Ganache, Hardhat) |
| `testnet` | `bool` | `False` | Test network |
| `chain_id` | `int \| str \| None` | `None` | Chain ID (EVM) or equivalent |

## Extending BlockchainType

`BlockchainType` is an empty enum. Define your own values by subclassing:

```python
from enum import Enum
from financepype.platforms.blockchain import BlockchainType

class ChainType(BlockchainType):
    EVM = "EVM"
    COSMOS = "COSMOS"
    SOLANA = "SOLANA"
    SUI = "SUI"
```

## Comparing Platforms

Platforms support standard Python equality and hashing based on their identifier and additional keyword arguments used during construction.

```python
binance_a = Platform(identifier="binance")
binance_b = Platform(identifier="binance")
assert binance_a == binance_b    # True (same object)
assert hash(binance_a) == hash(binance_b)

different = Platform(identifier="coinbase")
assert binance_a != different
```

## Using Platforms in Context

Platforms are used consistently throughout the framework:

```python
from financepype.platforms.platform import Platform
from financepype.assets.factory import AssetFactory
from financepype.owners.owner import OwnerIdentifier
from financepype.markets.trading_pair import TradingPair

platform = Platform(identifier="binance")

# Assets are scoped to a platform
btc = AssetFactory.get_asset(platform, "BTC")

# Owner identifiers embed the platform
owner = OwnerIdentifier(platform=platform, name="trader1")
print(owner.identifier)  # binance:trader1

# Trading pairs are platform-agnostic (no platform field on TradingPair itself)
# but rules and assets connect them to platforms
pair = TradingPair(name="BTC-USDT")
```
