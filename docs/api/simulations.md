# API Reference — Simulations

## financepype.simulations.balances.tracking.tracker

### BalanceType

```
class BalanceType(Enum)
```

| Value | Description |
|-------|-------------|
| `TOTAL` | All owned assets |
| `AVAILABLE` | Assets free for trading |

### BalanceUpdateType

```
class BalanceUpdateType(Enum)
```

| Value | Description |
|-------|-------------|
| `SNAPSHOT` | Complete balance replacement |
| `DIFFERENTIAL` | Incremental change |
| `SIMULATED` | Hypothetical change |

### BalanceChange

```
class BalanceChange(BaseModel)
```

Record of a single balance modification.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime` | When the change occurred |
| `asset` | `Asset` | Asset affected |
| `amount` | `Decimal` | Change amount (positive = increase) |
| `reason` | `str` | Human-readable cause |
| `balance_type` | `BalanceType` | TOTAL or AVAILABLE |
| `update_type` | `BalanceUpdateType` | How the change was applied |

### BalanceTracker

```
class BalanceTracker
```

**Constructor**

```python
BalanceTracker(track_history: bool = False)
```

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `balance_history` | `list[BalanceChange]` | All recorded changes (copy) |
| `total_balances` | `dict[Asset, Decimal]` | All balances (copy) |
| `available_balances` | `dict[Asset, Decimal]` | Available balances (copy) |
| `positions` | `dict[DerivativeContract, Position]` | Open positions (copy) |
| `locks` | `dict[Asset, dict[str, BalanceLock]]` | Locked balances (copy) |

**Balance Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_balance` | `(asset, amount, reason, balance_type) -> None` | Increase balance |
| `remove_balance` | `(asset, amount, reason, balance_type) -> None` | Decrease; raises if insufficient |
| `set_balance` | `(asset, amount, reason, balance_type) -> BalanceChange` | Overwrite to exact amount |
| `set_balances` | `(new_balances, reason, balance_type, complete_update=False) -> list[BalanceChange]` | Bulk set |

**Query Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_balance` | `(asset, balance_type) -> Decimal` | Raw balance |
| `get_unlocked_balance` | `(asset) -> Decimal` | Available minus all lock remainders |
| `get_locked_balance` | `(asset, purpose) -> Decimal` | Total locked for purpose |
| `get_available_locked_balance` | `(asset, purpose) -> Decimal` | Remaining in lock |
| `get_available_balance` | `(asset, purpose) -> Decimal` | Unlocked + available-in-lock |

**Position Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `set_position` | `(position, reason, balance_type) -> None` | Update position |
| `get_position` | `(asset: DerivativeContract) -> Position \| None` | Retrieve position |
| `remove_position` | `(asset: DerivativeContract) -> Position \| None` | Remove and adjust balances |

**Lock Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `lock_balance` | `(lock: BalanceLock) -> BalanceLock` | Lock portion of available |
| `release_locked_balance` | `(asset, purpose, amount) -> None` | Partially release lock |
| `release_all_locked_balances` | `(asset) -> None` | Release all locks for asset |
| `lock_multiple_balances` | `(locks: list[BalanceLock]) -> list[BalanceLock]` | Atomic multi-lock |
| `simulate_locks` | `(locks: list[BalanceLock]) -> bool` | Test lockability without effect |
| `use_locked_balance` | `(asset, purpose, amount) -> None` | Mark portion as used |
| `freeze_locked_balance` | `(asset, purpose, amount) -> None` | Freeze portion |
| `freeze_multiple_locked_balances` | `(list[tuple[asset, purpose, amount]]) -> None` | Atomic multi-freeze |
| `unfreeze_locked_balance` | `(asset, purpose, amount) -> None` | Unfreeze portion |

**History Methods**

- `record_balance_change(change: BalanceChange) -> None` — no-op if `track_history=False`
- `clear_balance_history() -> None`

---

## financepype.simulations.balances.tracking.lock

### BalanceLock

```
class BalanceLock
```

Reserves a portion of available balance for a specific purpose.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `asset` | `Asset` | The locked asset |
| `amount` | `Decimal` | Total locked amount |
| `purpose` | `str` | Identifier for what the lock is for |

**Properties**

- `remaining -> Decimal` — amount not yet used or frozen
- `used -> Decimal` — amount marked as consumed
- `frozen -> Decimal` — amount committed

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `add` | `(other: BalanceLock) -> None` | Merge another lock into this one |
| `release` | `(amount: Decimal) -> None` | Free locked amount |
| `use` | `(amount: Decimal) -> None` | Mark amount as used |
| `freeze` | `(amount: Decimal) -> None` | Commit amount |
| `unfreeze` | `(amount: Decimal) -> None` | Un-commit amount |

---

## financepype.simulations.balances.engines.engine

### BalanceEngine

```
class BalanceEngine [abstract]
```

Simulates cashflows for one type of trading operation.

**Class Methods** (all abstract)

| Method | Signature | Returns |
|--------|-----------|---------|
| `get_involved_assets` | `(operation_details: Any) -> list[AssetCashflow]` | Assets without amounts |
| `get_opening_outflows` | `(operation_details: Any) -> list[AssetCashflow]` | Assets leaving at open |
| `get_opening_inflows` | `(operation_details: Any) -> list[AssetCashflow]` | Assets arriving at open |
| `get_closing_outflows` | `(operation_details: Any) -> list[AssetCashflow]` | Assets leaving at close |
| `get_closing_inflows` | `(operation_details: Any) -> list[AssetCashflow]` | Assets arriving at close |
| `get_complete_simulation` | `(operation_details: Any) -> OperationSimulationResult` | All cashflows combined |

`get_complete_simulation` is concrete — it calls the four abstract methods and builds an `OperationSimulationResult`.

---

## financepype.simulations.balances.engines.models

### CashflowType

`INFLOW`, `OUTFLOW`

### InvolvementType

`OPENING`, `CLOSING`, `SETTLEMENT`

### CashflowReason

`OPERATION`, `FEE`, `PNL`, `FUNDING`, `INTEREST`, `REWARD`, `MARGIN`, `COLLATERAL`

### AssetCashflow

Represents one leg of a cashflow.

| Field | Type | Description |
|-------|------|-------------|
| `asset` | `Asset` | Asset flowing |
| `involvement_type` | `InvolvementType` | At opening, closing, or settlement |
| `cashflow_type` | `CashflowType` | In or out |
| `reason` | `CashflowReason` | Why this flow exists |
| `amount` | `Decimal \| None` | Amount (None = involvement only) |
| `period_index` | `int \| None` | Period index for multi-period simulations |
| `timestamp` | `int \| None` | Timestamp for settlement events |

### OperationSimulationResult

| Field | Type | Description |
|-------|------|-------------|
| `operation_details` | `Any` | Input operation details |
| `cashflows` | `list[AssetCashflow]` | All cashflows |

**Properties**

- `opening_outflows -> dict[Asset, Decimal]`
- `opening_inflows -> dict[Asset, Decimal]`
- `closing_outflows -> dict[Asset, Decimal]`
- `closing_inflows -> dict[Asset, Decimal]`

### PeriodicSimulationResult

| Field | Type | Description |
|-------|------|-------------|
| `operation_details` | `Any` | Base operation details |
| `period_results` | `list[OperationSimulationResult]` | Per-period results |

**Properties**

- `total_cashflows -> list[AssetCashflow]`
- `total_by_asset -> dict[Asset, Decimal]`

**Methods**

- `cashflows_at(timestamp: int) -> list[AssetCashflow]`
- `cashflows_in_range(start: int, end: int) -> list[AssetCashflow]`

---

## Engine Reference

### Lifecycle Engines (BalanceEngine)

| Engine Module | Class | Use Case |
|---------------|-------|----------|
| `engines.spot` | `SpotBalanceEngine` | Spot trades |
| `engines.perpetual` | `PerpetualBalanceEngine` | Perpetual futures |
| `engines.option` | `OptionBalanceEngine` | Options |
| `engines.borrowing` | `BorrowBalanceEngine` | Borrow/repay lifecycle |
| `engines.staking` | `StakingBalanceEngine` | Stake/unstake lifecycle |
| `engines.multiengine` | `BalanceMultiEngine` | Trade engine router |
| `engines.dashboard` | `Dashboard` | Portfolio aggregation |

### Settlement Engines (SettlementEngine)

| Engine Module | Class | Use Case |
|---------------|-------|----------|
| `engines.funding` | `FundingSettlementEngine` | Funding payments |
| `engines.borrowing` | `InterestSettlementEngine` | Interest accrual |
| `engines.staking` | `RewardSettlementEngine` | Reward distribution |
| `engines.periodic` | `PeriodicSimulator` | Multi-period simulation |

Lifecycle engines implement `BalanceEngine` (4-phase model). Settlement engines implement `SettlementEngine` (single-payment model).

---

## financepype.simulations.simulation

### BalanceSimulationEngine

```
class BalanceSimulationEngine
```

Combines a `BalanceTracker` with balance engines to simulate and apply trading operations.

**Constructor**

```python
BalanceSimulationEngine(tracker: BalanceTracker)
```

**Methods**

- `simulate_order(details) -> OperationSimulationResult`
- `apply_simulation_result(result: OperationSimulationResult) -> None`
