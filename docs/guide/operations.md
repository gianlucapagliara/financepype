# Operations

The `operations` module is the core of FinancePype's trading lifecycle management. It defines the base `Operation` type and two concrete implementations: order operations (for exchange orders) and blockchain transactions.

## Overview

Every trading action — placing an order, cancelling it, broadcasting a blockchain transaction — is modelled as an `Operation`. Operations have:

- A **client ID** assigned before submission
- An **operator ID** assigned by the exchange or blockchain after acceptance
- A **current state** that progresses through a defined lifecycle
- An async event that resolves when the operator ID is known

## Operation (Base Class)

```python
from financepype.operations.operation import Operation
```

Key attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `client_operation_id` | `str` | Client-assigned unique identifier |
| `operator_operation_id` | `Any` | Exchange/chain-assigned identifier (set after confirmation) |
| `owner_identifier` | `OwnerIdentifier` | The account that owns this operation |
| `creation_timestamp` | `float` | Unix timestamp at creation |
| `last_update_timestamp` | `float` | Unix timestamp of last state change |
| `current_state` | `Any` | Current lifecycle state |
| `other_data` | `dict` | Extra operation-specific data |

Key method:

- `update_operator_operation_id(id)` — can only be called once; sets the operator ID and signals the async event
- `process_operation_update(update)` — abstract; processes state changes

## Fees

`OperationFee` represents a trading fee.

```python
from decimal import Decimal
from financepype.operations.fees import OperationFee, FeeType, FeeImpactType

# 0.1% maker fee deducted from returns
fee = OperationFee(
    amount=Decimal("0.1"),
    fee_type=FeeType.PERCENTAGE,
    impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS,
)

# $5 flat fee added to costs
flat_fee = OperationFee(
    amount=Decimal("5"),
    fee_type=FeeType.ABSOLUTE,
    impact_type=FeeImpactType.ADDED_TO_COSTS,
)
```

`FeeType`:
- `PERCENTAGE` — percent of order value (must be ≤ 100)
- `ABSOLUTE` — fixed amount

`FeeImpactType`:
- `ADDED_TO_COSTS` — increases the cost of the operation
- `DEDUCTED_FROM_RETURNS` — reduces the proceeds of the operation

## OperationProposal

`OperationProposal` is an abstract base for pre-trade analysis. Before submitting an operation, a proposal can estimate costs, fees, and returns.

```python
from financepype.operations.proposal import OperationProposal
```

Subclasses must implement:

- `_prepare_update()` — pre-calculation setup
- `_update_costs()` — populate `potential_costs`
- `_update_fees()` — populate `potential_fees`
- `_update_returns()` — populate `potential_returns`
- `_update_totals()` — combine into `potential_total_costs` and `potential_total_returns`

Call `proposal.update_proposal()` to trigger the calculation. If any step fails, all potential values are reset to `None`.

```python
proposal = MyProposal(purpose="buy BTC")
proposal.update_proposal()

if proposal.initialized:
    print(proposal.potential_costs)
    print(proposal.potential_fees)
```

## OperationTracker

`OperationTracker` manages the lifecycle of in-flight operations. It maintains three buckets:

1. **Active** (`_in_flight_operations`) — submitted, awaiting completion
2. **Cached** (`_cached_operations`) — recently completed, TTL = 30 seconds, max 1000 entries
3. **Lost** (`_lost_operations`) — could not be reconciled

```python
from financepype.operations.tracker import OperationTracker
from eventspype.pub.multipublisher import MultiPublisher

publisher = MultiPublisher()
tracker = OperationTracker(event_publishers=[publisher])

# Start tracking
tracker.start_tracking_operation(order)

# Update the operator ID when exchange confirms
tracker.update_operator_operation_id("client_001", "exchange_abc")

# Fetch by client or operator ID
op = tracker.fetch_tracked_operation(client_operation_id="client_001")
op = tracker.fetch_updatable_operation(operator_operation_id="exchange_abc")

# Move to cache when done
tracker.stop_tracking_operation("client_001")

# Trigger events
from eventspype.pub.publication import EventPublication
tracker.trigger_event(EventPublication(...), event_data)
```

## Orders

### Order Models

```python
from financepype.operations.orders.models import (
    OrderType, OrderModifier, TradeType, OrderState,
    PositionAction, PositionMode, PriceType,
    OrderUpdate, TradeUpdate,
)
```

**OrderType**:
- `MARKET` — execute immediately at best available price
- `LIMIT` — execute at specified price or better
- `LIMIT_MAKER` — post-only limit order (deprecated alias)

**TradeType**:
- `BUY`
- `SELL`
- `RANGE` — not supported in orders, only in analysis

**OrderModifier**:
- `POST_ONLY` — order must go into the book; rejected if it would match immediately
- `REDUCE_ONLY` — can only reduce an existing position
- `IMMEDIATE_OR_CANCEL` — fill what's possible, cancel the rest
- `FILL_OR_KILL` — fill entirely or cancel entirely
- `DAY` — day order
- `AT_THE_OPEN` — open order modifier

**PositionAction** (for derivatives):
- `OPEN` — open a new position
- `CLOSE` — close an existing position
- `FLIP` — close and reverse
- `NIL` — no position action (spot)

**OrderState lifecycle**:

```
PENDING_CREATE → OPEN → PARTIALLY_FILLED → FILLED
              → FAILED
              → PENDING_CANCEL → CANCELED
```

### OrderOperation

```python
from financepype.operations.orders.order import OrderOperation
```

Full attributes:

| Attribute | Description |
|-----------|-------------|
| `trading_pair` | The market being traded |
| `order_type` | MARKET or LIMIT |
| `trade_type` | BUY or SELL |
| `amount` | Order size in base currency |
| `price` | Limit price (None for market orders) |
| `modifiers` | Set of `OrderModifier` values |
| `leverage` | Leverage multiplier (default 1 for spot) |
| `position` | `PositionAction` for derivatives |
| `executed_amount_base` | Total base filled so far |
| `executed_amount_quote` | Total quote value of fills |
| `order_fills` | Dict of trade_id → `TradeUpdate` |

Key properties:

```python
order.is_open           # True while pending/open/pending_cancel
order.is_done           # True when filled/cancelled/failed
order.is_filled         # True when fully filled
order.remaining_amount  # amount - executed_amount_base
order.average_executed_price  # volume-weighted average fill price
```

Async helpers:

```python
# Wait until exchange assigns an order ID (with timeout)
exchange_id = await order.get_exchange_order_id(timeout=10)

# Wait until fully filled
await order.wait_until_completely_filled()
```

Updating:

```python
# State update from exchange
order.process_operation_update(OrderUpdate(...))

# Trade fill
order.process_operation_update(TradeUpdate(...))
```

### OrderProposal

`OrderProposal` extends `OperationProposal` for pre-trade cost analysis of orders. Subclass it and implement the abstract methods.

## Transactions

### BlockchainTransactionState

```
PENDING_BROADCAST → BROADCASTED → CONFIRMED → FINALIZED
                 → FAILED
                 → REJECTED
                 → CANCELLED
```

### BlockchainTransaction

```python
from financepype.operations.transactions.transaction import BlockchainTransaction
```

Key properties:

```python
tx.is_pending            # PENDING_BROADCAST or BROADCASTED
tx.is_broadcasted        # BROADCASTED
tx.is_completed          # CONFIRMED or FINALIZED
tx.is_finalized          # FINALIZED
tx.is_failure            # FAILED or REJECTED
tx.is_cancelled          # CANCELLED
tx.is_closed             # any terminal state
```

Abstract methods that subclasses must implement:

- `can_be_modified` — whether gas price can be adjusted
- `can_be_cancelled` — whether the tx can be cancelled
- `can_be_speeded_up` — whether the tx can be accelerated
- `process_receipt(receipt)` — handle the chain receipt

Updating:

```python
from financepype.operations.transactions.models import (
    BlockchainTransactionUpdate, BlockchainTransactionState
)

update = BlockchainTransactionUpdate(
    update_timestamp=1700000000.0,
    transaction_id=tx_hash,
    new_state=BlockchainTransactionState.CONFIRMED,
)
tx.process_operation_update(update)
```

### BlockchainTransactionFee

Extends `OperationFee` with blockchain-specific defaults: `fee_type=ABSOLUTE`, `impact_type=ADDED_TO_COSTS`.

### TransactionTracker

Works identically to `OperationTracker` but typed for `BlockchainTransaction` operations.
