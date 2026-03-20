# API Reference — Operations

## financepype.operations.fees

### FeeImpactType

```
class FeeImpactType(Enum)
```

| Value | Description |
|-------|-------------|
| `ADDED_TO_COSTS` | Fee increases operation cost |
| `DEDUCTED_FROM_RETURNS` | Fee reduces operation returns |

### FeeType

```
class FeeType(Enum)
```

| Value | Description |
|-------|-------------|
| `PERCENTAGE` | Fee as a % of operation amount (≤ 100) |
| `ABSOLUTE` | Fixed fee amount |

### OperationFee

```
class OperationFee(BaseModel)
```

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| `amount` | `Decimal` | `>= 0` | Fee amount |
| `asset` | `Asset \| None` | | Fee denomination asset |
| `fee_type` | `FeeType` | | Calculation method |
| `impact_type` | `FeeImpactType` | | How it impacts the trade |

**Validator**: `validate_fee` — rejects percentage > 100.

---

## financepype.operations.operation

### Operation

```
class Operation(BaseModel) [abstract]
```

Base for all trading operations. Uses `ConfigDict(arbitrary_types_allowed=True)`.

**Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `client_operation_id` | `str` | required | Client-assigned ID |
| `operator_operation_id` | `Any \| None` | `None` | Exchange/chain-assigned ID |
| `owner_identifier` | `OwnerIdentifier` | required | Account owner |
| `creation_timestamp` | `float` | required | Unix timestamp at creation |
| `last_update_timestamp` | `float` | `0.0` | Last state change time |
| `current_state` | `Any` | required | Current lifecycle state |
| `other_data` | `dict[str, Any]` | `{}` | Extra data |
| `operator_operation_id_update_event` | `asyncio.Event` | `Event()` | Async signal for ID update |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `update_operator_operation_id` | `(id: Any) -> None` | Set operator ID once; raises if changing |
| `process_operation_update` | `(update: Any) -> bool` [abstract] | Process a state update |

---

## financepype.operations.proposal

### OperationProposal

```
class OperationProposal(BaseModel, ABC)
```

Pre-trade cost/return estimation. `ConfigDict(arbitrary_types_allowed=True)`.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `purpose` | `str` | Why this operation is being proposed |
| `client_id_prefix` | `str` | Optional prefix for client IDs |
| `potential_costs` | `dict[Asset, Decimal] \| None` | Estimated costs per asset |
| `potential_returns` | `dict[Asset, Decimal] \| None` | Estimated returns per asset |
| `potential_fees` | `list[OperationFee] \| None` | Estimated fees |
| `potential_total_costs` | `dict[Asset, Decimal] \| None` | Total costs including fees |
| `potential_total_returns` | `dict[Asset, Decimal] \| None` | Total returns after fees |
| `executed_operation` | `Operation \| None` | Set when executed |

**Properties**

- `initialized -> bool` — True if `potential_costs` is not None
- `executed -> bool` — True if `executed_operation` is not None

**Methods**

| Method | Description |
|--------|-------------|
| `update_proposal() -> None` | Run all calculation phases |
| `_prepare_update()` [abstract] | Pre-calculation hook |
| `_update_costs()` [abstract] | Populate `potential_costs` |
| `_update_fees()` [abstract] | Populate `potential_fees` |
| `_update_returns()` [abstract] | Populate `potential_returns` |
| `_update_totals()` [abstract] | Populate `potential_total_costs/returns` |

---

## financepype.operations.tracker

### OperationTracker

```
class OperationTracker
```

**Class Attributes**

| Attribute | Value | Description |
|-----------|-------|-------------|
| `MAX_CACHE_SIZE` | `1000` | Max cached operations |
| `CACHED_OPERATION_TTL` | `30.0` | Seconds to keep in cache |

**Constructor**

```python
OperationTracker(
    event_publishers: list[MultiPublisher],
    lost_operation_count_limit: int = 3,
)
```

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `active_operations` | `dict[str, Operation]` | Currently tracked |
| `cached_operations` | `dict[str, Operation]` | Recently completed |
| `lost_operations` | `dict[str, Operation]` | Failed/lost |
| `all_updatable_operations` | `dict[str, Operation]` | Active + lost |
| `all_operations` | `dict[str, Operation]` | All three buckets |

**Tracking Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `start_tracking_operation` | `(operation: Operation) -> None` | Add to active |
| `stop_tracking_operation` | `(client_id: str) -> None` | Move to cache |
| `restore_tracking_states` | `(states: dict) -> None` | Restore from saved state |

**Fetch Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `fetch_operation` | `(client_id?, operator_id?, operations?) -> Operation \| None` | General search |
| `fetch_tracked_operation` | `(client_id?, operator_id?) -> Operation \| None` | Search active |
| `fetch_cached_operation` | `(client_id?, operator_id?) -> Operation \| None` | Search cache |
| `fetch_updatable_operation` | `(client_id?, operator_id?) -> Operation \| None` | Search active+lost |

**Update Methods**

- `update_operator_operation_id(client_id, operator_id) -> Operation | None`

**Event Methods**

- `trigger_event(event_publication, event) -> None` — publishes to all registered publishers
