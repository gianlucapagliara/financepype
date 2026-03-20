# API Reference — Transactions

## financepype.operations.transactions.models

### BlockchainTransactionState

```
class BlockchainTransactionState(Enum)
```

| Value | String | Description |
|-------|--------|-------------|
| `PENDING_BROADCAST` | `"pending"` | Created, not yet sent |
| `BROADCASTED` | `"broadcasted"` | Sent to network |
| `CONFIRMED` | `"completed"` | Included in a block |
| `FINALIZED` | `"finalized"` | Enough confirmations |
| `FAILED` | `"failed"` | Execution failed on chain |
| `REJECTED` | `"rejected"` | Rejected by simulation or node |
| `CANCELLED` | `"cancelled"` | Cancelled by user |

### BlockchainTransactionFee

```
class BlockchainTransactionFee(OperationFee)
```

Extends `OperationFee` with blockchain-specific defaults:

- `fee_type` always `FeeType.ABSOLUTE`
- `impact_type` always `FeeImpactType.ADDED_TO_COSTS`
- `asset` is `BlockchainAsset | None`

### BlockchainTransactionReceipt

```
class BlockchainTransactionReceipt(BaseModel)  [frozen]
```

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | `BlockchainIdentifier` | The transaction hash |

Subclasses may add `data: Any` for chain-specific receipt fields.

### BlockchainTransactionUpdate

```
class BlockchainTransactionUpdate(BaseModel)
```

| Field | Type | Description |
|-------|------|-------------|
| `update_timestamp` | `float` | Unix timestamp of update |
| `client_transaction_id` | `str \| None` | Client-side ID |
| `transaction_id` | `BlockchainIdentifier \| None` | Chain hash |
| `new_state` | `BlockchainTransactionState` | Target state |
| `receipt` | `BlockchainTransactionReceipt \| None` | Receipt if available |
| `explorer_link` | `str \| None` | Block explorer URL |
| `other_data` | `dict[str, Any]` | Extra chain-specific data |

**Validator**: `validate_identifiers` — at least one of `client_transaction_id` or `transaction_id` must be present.

---

## financepype.operations.transactions.transaction

### BlockchainTransaction

```
class BlockchainTransaction(Operation) [abstract]
```

Manages the full lifecycle of a blockchain transaction.

**Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `current_state` | `BlockchainTransactionState` | `PENDING_BROADCAST` | Lifecycle state |
| `operator_operation_id` | `BlockchainIdentifier \| None` | `None` | Transaction hash |
| `signed_transaction` | `Any \| None` | `None` | Signed tx data |
| `receipt` | `BlockchainTransactionReceipt \| None` | `None` | On-chain receipt |
| `fee` | `BlockchainTransactionFee \| None` | `None` | Fee structure |
| `explorer_link` | `str \| None` | `None` | Block explorer URL |

**Properties (from Operation)**

- `client_transaction_id -> str` — alias for `client_operation_id`
- `transaction_id -> BlockchainIdentifier | None` — alias for `operator_operation_id`
- `paid_fee -> BlockchainTransactionFee | None` [abstract]

**Abstract Properties** (subclasses must implement)

| Property | Type | Description |
|----------|------|-------------|
| `can_be_modified` | `bool` | Can gas price be adjusted? |
| `can_be_cancelled` | `bool` | Can the tx be cancelled? |
| `can_be_speeded_up` | `bool` | Can tx be accelerated? |

**Status Properties**

| Property | Condition |
|----------|-----------|
| `is_pending` | `PENDING_BROADCAST` or `BROADCASTED` |
| `is_pending_broadcast` | `PENDING_BROADCAST` |
| `is_broadcasted` | `BROADCASTED` |
| `is_failure` | `FAILED` or `REJECTED` |
| `is_completed` | `CONFIRMED` or `FINALIZED` |
| `is_finalized` | `FINALIZED` |
| `is_cancelled` | `CANCELLED` |
| `is_closed` | `CONFIRMED`, `FINALIZED`, `FAILED`, `REJECTED`, or `CANCELLED` |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `process_operation_update` | `(update: BlockchainTransactionUpdate) -> bool` | Apply state update |
| `update_signed_transaction` | `(signed_tx: Any) -> None` | Set signed tx (once only) |
| `process_receipt` | `(receipt: BlockchainTransactionReceipt) -> bool` [abstract] | Handle chain receipt |
| `from_transaction` | `classmethod (tx, **kwargs) -> Self` | Copy constructor |

**`process_operation_update` logic**

1. If `transaction_id` is None, set from update (first confirmation).
2. Reject updates where `transaction_id` doesn't match.
3. Reject updates older than `last_update_timestamp`.
4. Update state, explorer link, and process receipt if present.

---

## financepype.operations.transactions.tracker

### TransactionTracker

Extends `OperationTracker` for `BlockchainTransaction` instances. Interface is identical to `OperationTracker`.

---

## financepype.operations.transactions.proposal

### TransactionProposal

```
class TransactionProposal(OperationProposal)
```

Extends `OperationProposal` for blockchain transaction pre-flight analysis. Implement the five abstract methods from `OperationProposal`.

---

## financepype.operations.transactions.events

Transaction events published through the operator's `MultiPublisher`. Event classes are used with `TransactionTracker.trigger_event(...)`.

---

## financepype.operators.blockchains.identifier

### BlockchainIdentifier

Represents a chain-native identifier (e.g., transaction hash, contract address). Used as `operator_operation_id` in `BlockchainTransaction` and as `identifier` in `BlockchainAsset`.

```python
from financepype.operators.blockchains.identifier import BlockchainIdentifier
```
