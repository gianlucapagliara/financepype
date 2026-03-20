# Assets

The `assets` module defines the type hierarchy for all tradable instruments in FinancePype. Every asset is bound to a `Platform` and carries a typed identifier, allowing the framework to treat assets from different exchanges consistently.

## Asset Hierarchy

```
Asset (abstract base)
├── CentralizedAsset          — assets on centralised exchanges
│   ├── SpotAsset             — simple spot tokens (BTC, ETH, USDT)
│   └── DerivativeContract    — futures/perpetuals/options contracts
└── BlockchainAsset           — on-chain tokens with decimal precision
```

## AssetIdentifier

`AssetIdentifier` is an immutable Pydantic model used as the string key for centralized assets. It is frozen and hashable, so it can be used as a dict key or in sets.

```python
from financepype.assets.asset_id import AssetIdentifier

btc_id = AssetIdentifier(value="BTC")
usdt_id = AssetIdentifier(value="USDT")

print(str(btc_id))    # BTC
print(btc_id == usdt_id)  # False
d = {btc_id: "Bitcoin"}   # valid dict key
```

## Asset (Base Class)

`Asset` is the abstract base for all asset types. It is also a frozen Pydantic model.

```python
from financepype.assets.asset import Asset
```

Key attributes:

- `platform` (`Platform`) — the exchange or chain this asset lives on
- `identifier` (`Any`) — asset-specific identifier (typed in subclasses)

## SpotAsset

`SpotAsset` represents a basic tradable token on a centralized exchange.

```python
from financepype.platforms.platform import Platform
from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.spot import SpotAsset

platform = Platform(identifier="binance")
btc = SpotAsset(
    platform=platform,
    identifier=AssetIdentifier(value="BTC"),
    name="Bitcoin",   # optional human-readable name
)

print(btc.symbol)   # BTC
print(btc.name)     # Bitcoin
print(btc.platform) # binance
```

## CentralizedAsset

`CentralizedAsset` is the direct parent of `SpotAsset` and `DerivativeContract`. It exposes a `symbol` property that returns the identifier's string value.

## DerivativeContract

`DerivativeContract` represents a futures, perpetual, or option position. It validates that the trading pair name encodes a derivative market type (not SPOT).

```python
from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.platforms.platform import Platform

platform = Platform(identifier="binance")

long_perp = DerivativeContract(
    platform=platform,
    identifier=AssetIdentifier(value="BTC-USDT-PERPETUAL"),
    side=DerivativeSide.LONG,
)

print(long_perp.symbol)           # BTC-USDT-PERPETUAL
print(long_perp.trading_pair)     # TradingPair(name=BTC-USDT-PERPETUAL)
print(long_perp.market_info.is_perpetual)  # True
```

`DerivativeSide` values:

| Value | Meaning |
|-------|---------|
| `LONG` | Long position (betting price rises) |
| `SHORT` | Short position (betting price falls) |
| `BOTH` | Market-making / both sides |

!!! note
    Only `LONG` and `SHORT` are valid on an actual `DerivativeContract`. `BOTH` is used by `AssetFactory` as a default placeholder.

## BlockchainAsset

`BlockchainAsset` represents a token that lives on a blockchain. It uses a `BlockchainIdentifier` (e.g., a contract address) and carries decimal precision information.

```python
from financepype.assets.blockchain import BlockchainAsset, BlockchainAssetData
from financepype.operators.blockchains.identifier import BlockchainIdentifier
from financepype.platforms.blockchain import BlockchainPlatform
from decimal import Decimal

# BlockchainPlatform requires a blockchain type enum (user-defined)
# platform = BlockchainPlatform(identifier="ethereum", type=MyBlockchainType.EVM)

asset_data = BlockchainAssetData(name="USD Coin", symbol="USDC", decimals=6)
# asset = BlockchainAsset(platform=platform, identifier=contract_id, data=asset_data)

# Convert between raw and decimal amounts
# usdc.convert_to_decimals(1_000_000)  # Decimal('1.000000')
# usdc.convert_to_raw(Decimal("1.5"))  # 1500000
```

Key methods:

- `convert_to_decimals(raw_amount: int) -> Decimal` — divide by 10^decimals
- `convert_to_raw(decimal_amount: Decimal) -> int` — multiply by 10^decimals

## AssetFactory

`AssetFactory` is a global factory and cache for asset instances. It guarantees that the same `(platform, symbol, side)` tuple always returns the same object.

```python
from financepype.platforms.platform import Platform
from financepype.assets.factory import AssetFactory
from financepype.assets.contract import DerivativeSide

platform = Platform(identifier="binance")

# Spot asset (default when symbol has no market type suffix)
btc = AssetFactory.get_asset(platform, "BTC")

# Derivative contract
long_perp = AssetFactory.get_asset(
    platform, "BTC-USDT-PERPETUAL", side=DerivativeSide.LONG
)

# Cache info
info = AssetFactory.get_cache_info()
print(info["cache_size"])           # number of cached assets
print(info["registered_creators"])  # number of market type handlers

# Clear cache (useful in tests)
AssetFactory.clear_cache()
AssetFactory.reset()  # also clears and re-registers default creators
```

### Custom Asset Creators

You can register a custom creator for any `MarketType`:

```python
from financepype.assets.factory import AssetFactory
from financepype.markets.market import MarketType
from financepype.platforms.platform import Platform

def my_option_creator(platform, symbol, kwargs):
    # return a custom option asset instance
    ...

AssetFactory.register_creator(MarketType.CALL_OPTION, my_option_creator)
```

## Immutability

All asset classes use `model_config = ConfigDict(frozen=True)`. Once created, their fields cannot be mutated. This ensures safe use as dictionary keys and in sets across the entire framework.
