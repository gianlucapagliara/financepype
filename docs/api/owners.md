# API Reference — Owners

## financepype.owners.owner

### OwnerIdentifier

```
class OwnerIdentifier(BaseModel)  [frozen]
```

Immutable, hashable identifier combining a platform and a name.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `platform` | `Platform` | The platform |
| `name` | `str \| None` | Account name; `None` → "unknown" |

**Properties**

- `identifier -> str` — `"platform_id:name"` or `"platform_id:unknown"`

**Special Methods**

- `__repr__` → `"<Owner: platform_id:name>"`

---

### OwnerConfiguration

```
class OwnerConfiguration(BaseModel)
```

| Field | Type |
|-------|------|
| `identifier` | `OwnerIdentifier` |

---

### Owner

```
class Owner(MultiPublisher) [abstract]
```

Abstract base for trading account holders. Extends `eventspype.MultiPublisher`.

**Constructor**

```python
Owner(configuration: OwnerConfiguration)
```

Creates a `BalanceTracker` and a `_balances_ready` `asyncio.Event`.

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `identifier` | `OwnerIdentifier` | Account identity |
| `platform` | `Platform` | Delegated from identifier |
| `balance_tracker` | `BalanceTracker` | Balance storage |
| `current_timestamp` | `float` | Abstract — current time |

**Balance Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_balance` | `(currency: str) -> Decimal` | Total balance |
| `get_available_balance` | `(currency: str) -> Decimal` | Available balance |
| `get_all_balances` | `() -> dict[str, Decimal]` | All total balances |
| `get_all_available_balances` | `() -> dict[str, Decimal]` | All available balances |
| `set_balances` | `(total, available, complete_snapshot=False) -> tuple[dict, dict]` | Set multiple balances |

**`set_balances` signature**

```python
set_balances(
    total_balances: list[tuple[Asset, Decimal]],
    available_balances: list[tuple[Asset, Decimal]],
    complete_snapshot: bool = False,
    **kwargs,
) -> tuple[dict[str, Decimal], dict[str, Decimal]]
```

Returns dicts of changed assets. With `complete_snapshot=True`, assets not in the list are zeroed.

**Position Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_position` | `(trading_pair: str, side: DerivativeSide) -> Position \| None` | Single position |
| `get_all_positions` | `() -> dict[DerivativeContract, Position]` | All open positions |
| `set_position` | `(position: Position) -> None` | Set/update a position |
| `remove_position` | `(trading_pair: TradingPair, side: DerivativeSide) -> Position \| None` | Remove position |

**Abstract Methods** (subclasses must implement)

| Method | Description |
|--------|-------------|
| `update_all_balances() -> None` | Fetch all balances from source |
| `update_all_positions() -> None` | Fetch all positions from source |
| `update_balance(asset: Asset) -> None` | Fetch single asset balance |

---

## financepype.owners.multiowner

### MultiOwner

```
class MultiOwner
```

Aggregates multiple `Owner` instances, providing a unified balance and position view.

Useful for strategies operating across several accounts simultaneously.

---

## financepype.owners.factory

### OwnerFactory

```
class OwnerFactory
```

Registry for creating `Owner` instances.

**Class Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(identifier: str, factory: Callable) -> None` | Register a factory |
| `get` | `(identifier: str) -> Owner` | Create or retrieve |
