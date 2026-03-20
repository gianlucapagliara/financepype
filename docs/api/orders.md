# API Reference — Orders

## financepype.operations.orders.models

### OrderType

```
class OrderType(Enum)
```

| Value | Description |
|-------|-------------|
| `MARKET` | Execute immediately at best price |
| `LIMIT` | Execute at specified price or better |
| `LIMIT_MAKER` | Post-only limit (deprecated alias) |

**Methods**

- `is_limit_type() -> bool`
- `is_market_type() -> bool`

### OrderModifier

```
class OrderModifier(Enum)
```

| Value | Description |
|-------|-------------|
| `POST_ONLY` | Rejected if it would match immediately |
| `REDUCE_ONLY` | Can only decrease an existing position |
| `IMMEDIATE_OR_CANCEL` | Fill what's available, cancel the rest |
| `FILL_OR_KILL` | Fill entirely or cancel entirely |
| `DAY` | Day order |
| `AT_THE_OPEN` | Executes at market open |

### PositionAction

```
class PositionAction(Enum)
```

`OPEN`, `CLOSE`, `FLIP`, `NIL`

### PositionMode

```
class PositionMode(Enum)
```

`HEDGE`, `ONEWAY`

### PriceType

```
class PriceType(Enum)
```

`MidPrice`, `BestBid`, `BestAsk`, `LastTrade`, `LastOwnTrade`, `InventoryCost`, `Custom`

### TradeType

```
class TradeType(Enum)
```

| Value | Description |
|-------|-------------|
| `BUY` | Buy side |
| `SELL` | Sell side |
| `RANGE` | Range (used in analysis only, not orders) |

**Methods**

- `opposite() -> TradeType` — BUY↔SELL; raises for RANGE
- `to_position_side() -> DerivativeSide` — BUY→LONG, SELL→SHORT, RANGE→BOTH

### OrderState

```
class OrderState(Enum)
```

| Value | String | Meaning |
|-------|--------|---------|
| `PENDING_CREATE` | `"pending_create"` | Submitted, not yet acknowledged |
| `OPEN` | `"open"` | In order book |
| `PARTIALLY_FILLED` | `"partially_filled"` | Some fills received |
| `PENDING_CANCEL` | `"pending_cancel"` | Cancel requested |
| `CANCELED` | `"canceled"` | Cancelled |
| `FILLED` | `"filled"` | Completely filled |
| `FAILED` | `"failed"` | Exchange rejected |

### OrderUpdate

```
class OrderUpdate(BaseModel)
```

| Field | Type | Description |
|-------|------|-------------|
| `trading_pair` | `TradingPair` | Market |
| `update_timestamp` | `float` | Seconds since epoch |
| `new_state` | `OrderState` | Target state |
| `client_order_id` | `str \| None` | Client ID |
| `exchange_order_id` | `str \| None` | Exchange ID |
| `misc_updates` | `dict \| None` | Additional data |

### TradeUpdate

```
class TradeUpdate(BaseModel)
```

| Field | Type | Description |
|-------|------|-------------|
| `trade_id` | `str` | Unique trade ID |
| `client_order_id` | `str \| None` | Client order ID |
| `exchange_order_id` | `str` | Exchange order ID |
| `trading_pair` | `TradingPair` | Market |
| `trade_type` | `TradeType` | BUY or SELL |
| `fill_timestamp` | `float` | Fill time in seconds |
| `fill_price` | `Decimal` | Fill price |
| `fill_base_amount` | `Decimal` | Base quantity filled |
| `fill_quote_amount` | `Decimal` | Quote value of fill |
| `fee` | `OperationFee` | Associated fee |
| `group_order_id` | `str` | Group identifier (default `""`) |

**Properties**: `group_client_order_id -> str | None`

---

## financepype.operations.orders.order

### OrderOperation

```
class OrderOperation(Operation)
```

Extends `Operation` with order-specific state management.

**Additional Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `trading_pair` | `TradingPair` | required | Market |
| `order_type` | `OrderType` | required | MARKET or LIMIT |
| `trade_type` | `TradeType` | required | BUY or SELL |
| `amount` | `Decimal` | required | Order size |
| `price` | `Decimal \| None` | `None` | Limit price |
| `modifiers` | `set[OrderModifier]` | `set()` | Order modifiers |
| `group_order_id` | `str` | `""` | Group identifier |
| `leverage` | `int` | `1` | Leverage |
| `index_price` | `Decimal \| None` | `price` | Index price |
| `position` | `PositionAction` | `NIL` | Derivative position action |
| `executed_amount_base` | `Decimal` | `0` | Base filled so far |
| `executed_amount_quote` | `Decimal` | `0` | Quote value of fills |
| `order_fills` | `dict[str, TradeUpdate]` | `{}` | Fill records |
| `current_state` | `OrderState` | `PENDING_CREATE` | Lifecycle state |
| `completely_filled_event` | `asyncio.Event` | `Event()` | Signals full fill |

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `exchange_order_id` | `str \| None` | Alias for `operator_operation_id` |
| `group_client_order_id` | `str` | `f"{group_order_id}{client_operation_id}"` |
| `filled_amount` | `Decimal` | `executed_amount_base` |
| `remaining_amount` | `Decimal` | `amount - executed_amount_base` |
| `base_asset` | `Any` | `trading_pair.base` |
| `quote_asset` | `Any` | `trading_pair.quote` |
| `is_limit` | `bool` | `order_type == LIMIT` |
| `is_market` | `bool` | `order_type == MARKET` |
| `is_buy` | `bool` | `trade_type == BUY` |
| `average_executed_price` | `Decimal \| None` | Volume-weighted average |
| `is_pending_create` | `bool` | state == PENDING_CREATE |
| `is_pending_cancel_confirmation` | `bool` | state == PENDING_CANCEL |
| `is_open` | `bool` | PENDING_CREATE, OPEN, or PENDING_CANCEL |
| `is_done` | `bool` | terminal or fully filled |
| `is_filled` | `bool` | FILLED or executed >= amount |
| `is_failure` | `bool` | state == FAILED |
| `is_cancelled` | `bool` | state == CANCELED |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `process_operation_update` | `(update: OrderUpdate \| TradeUpdate) -> bool` | Route to correct handler |
| `is_valid_state_transition` | `(update: OrderUpdate) -> bool` | Validate state machine |
| `check_filled_condition` | `() -> None` | Set filled event if complete |
| `wait_until_completely_filled` | `async () -> None` | Await fill event |
| `get_exchange_order_id` | `async (timeout=10) -> str \| None` | Wait for exchange ID |
| `build_order_created_message` | `() -> str` | Human-readable creation log |

**Valid State Transitions**

| From | To |
|------|----|
| `PENDING_CREATE` | `OPEN`, `FAILED` |
| `OPEN` | `OPEN`, `PENDING_CANCEL`, `CANCELED`, `FILLED` |
| `PENDING_CANCEL` | `CANCELED`, `OPEN`, `FILLED` |

---

## financepype.operations.orders.proposal

### OrderProposal

```
class OrderProposal(OperationProposal)
```

Extends `OperationProposal` for order pre-trade analysis. No additional fields — implement the abstract methods from `OperationProposal`.

---

## financepype.operations.orders.tracker

### OrderTracker

Extends `OperationTracker` typed specifically for `OrderOperation` instances. Provides the same interface as `OperationTracker` with order-specific event triggers.

---

## financepype.operations.orders.events

Order events published to the `MultiPublisher` of the owning operator or owner. The specific event classes are defined here and used with `EventPublication` when calling `OperationTracker.trigger_event(...)`.
