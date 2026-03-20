# API Reference — Assets

## financepype.assets.asset_id

### AssetIdentifier

```
class AssetIdentifier(BaseModel)
```

Frozen, hashable identifier for assets on centralised exchanges.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `value` | `str` | The string identifier (e.g., "BTC") |

**Methods**

- `__str__() -> str` — returns `self.value`
- `__eq__(other) -> bool` — compares by `value`
- `__hash__() -> int` — hash of `value`

---

## financepype.assets.asset

### Asset

```
class Asset(BaseModel)
```

Abstract frozen base for all tradable assets. Subclasses must not mutate after construction.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `platform` | `Platform` | The exchange or chain this asset lives on |
| `identifier` | `Any` | Asset identifier (typed in subclasses) |

---

## financepype.assets.centralized_asset

### CentralizedAsset

```
class CentralizedAsset(Asset)
```

Base for assets on centralised exchanges. Typed identifier is `AssetIdentifier`.

**Fields** (inherited)

| Field | Type |
|-------|------|
| `platform` | `Platform` |
| `identifier` | `AssetIdentifier` |

**Properties**

- `symbol -> str` — returns `identifier.value`

---

## financepype.assets.spot

### SpotAsset

```
class SpotAsset(CentralizedAsset)
```

Represents a spot trading token (e.g., BTC, USDT, ETH).

**Additional Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str \| None` | `None` | Human-readable name (e.g., "Bitcoin") |

**Inherited Properties**

- `symbol -> str`

---

## financepype.assets.contract

### DerivativeSide

```
class DerivativeSide(Enum)
```

| Value | Description |
|-------|-------------|
| `LONG` | Long position |
| `SHORT` | Short position |
| `BOTH` | Both sides (market-making placeholder) |

### DerivativeContract

```
class DerivativeContract(CentralizedAsset)
```

Represents a derivative instrument (future, perpetual, option) with a defined side.

**Additional Fields**

| Field | Type | Description |
|-------|------|-------------|
| `side` | `DerivativeSide` | Must be `LONG` or `SHORT` |

**Validators**

- `validate_identifier` — ensures the symbol parses to a non-SPOT `MarketType`
- `validate_side` — ensures side is LONG or SHORT

**Properties**

- `trading_pair -> TradingPair` — `TradingPair(name=self.symbol)`
- `market_info -> MarketInfo` — parsed market information

---

## financepype.assets.blockchain

### BlockchainAssetData

```
class BlockchainAssetData(BaseModel)
```

Frozen metadata for a blockchain token.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Full name (e.g., "USD Coin") |
| `symbol` | `str` | Ticker symbol (e.g., "USDC") |
| `decimals` | `int` | Token decimals (e.g., 6 for USDC) |

### BlockchainAsset

```
class BlockchainAsset(Asset)
```

Represents an on-chain token with decimal precision.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `platform` | `BlockchainPlatform` | The blockchain network |
| `identifier` | `BlockchainIdentifier` | Contract address or similar |
| `data` | `BlockchainAssetData` | Token metadata |

**Methods**

- `convert_to_decimals(raw_amount: int) -> Decimal` — `raw_amount / 10^decimals`
- `convert_to_raw(decimal_amount: Decimal) -> int` — `int(decimal_amount * 10^decimals)`

---

## financepype.assets.factory

### AssetFactory

```
class AssetFactory
```

Global factory and cache for asset instances. All methods are `@classmethod`.

**Class Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `_cache` | `dict[tuple, Asset]` | Cache keyed on `(platform_id, symbol, side)` |
| `_creators` | `dict[MarketType, Callable]` | Creator functions per market type |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_asset` | `(platform, symbol, **kwargs) -> Asset` | Get or create an asset |
| `register_creator` | `(market_type, creator) -> None` | Register a custom creator |
| `register_default_creators` | `() -> None` | Register built-in spot/derivative creators |
| `create_spot` | `(platform, symbol, _) -> Asset` | Create a `SpotAsset` |
| `create_derivative` | `(platform, symbol, kwargs) -> Asset` | Create a `DerivativeContract` |
| `clear_cache` | `() -> None` | Remove all cached assets |
| `reset` | `() -> None` | Clear cache and re-register defaults |
| `get_cache_info` | `() -> dict[str, int]` | `{"cache_size": N, "registered_creators": M}` |
| `get_cached_assets` | `() -> list[tuple]` | List of cache keys |

**`get_asset` behaviour**

1. Check cache for `(platform.identifier, symbol, side)`.
2. Parse symbol with `MarketInfo.split_client_instrument_name`.
3. If a creator is registered for the market type, use it.
4. Otherwise, fall back to `SpotAsset`.
5. Store in cache and return.
