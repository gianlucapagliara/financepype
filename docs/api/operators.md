# API Reference — Operators

## financepype.operators.operator

### OperatorConfiguration

```
class OperatorConfiguration(BaseModel)
```

| Field | Type | Description |
|-------|------|-------------|
| `platform` | `Platform` | The platform to connect to |

### Operator

```
class Operator
```

Base class for all exchange/blockchain connectors.

**Constructor**

```python
Operator(configuration: OperatorConfiguration)
```

Creates a `NonceCreator` (microseconds) and a `MultiPublisher` internally.

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `configuration` | `OperatorConfiguration` | |
| `platform` | `Platform` | Delegated from configuration |
| `name` | `str` | `str(platform)` |
| `display_name` | `str` | Same as `name` by default |
| `current_timestamp` | `float` | Abstract — current exchange time |
| `publishing` | `MultiPublisher` | Event publisher |

### OperatorProcessor

```
class OperatorProcessor(NetworkProcessor)
```

Polling loop base class for REST-based connectors.

**Constructor**

```python
OperatorProcessor(operator: Operator)
```

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `update_loop` | `async (interval_seconds: float) -> None` | Poll loop; calls `_update_loop_fetch_updates` |
| `_update_loop_fetch_updates` | `async () -> None` [abstract] | Subclass implements actual fetch |
| `_sleep` | `async (seconds: float) -> None` | `asyncio.sleep` |

The loop waits on `_poll_notifier` (an `asyncio.Event`) before each poll, then clears it. On errors it sleeps 0.5 s and retries.

---

## financepype.operators.nonce_creator

### NonceCreator

```
class NonceCreator
```

Generates monotonically increasing unique integers for client operation IDs.

**Class Methods**

- `for_microseconds() -> NonceCreator` — uses microsecond timestamps

**Methods**

- `get_tracking_nonce() -> int` — returns the next unique integer

---

## financepype.operators.exchanges.exchange

### ExchangeOperator

```
class ExchangeOperator(Operator) [abstract]
```

Base for centralized exchange connectors. Adds order management, balance fetching, and rules tracking.

Subclasses implement exchange-specific REST and WebSocket logic.

---

## financepype.operators.exchanges.orderbook_exchange

### OrderbookExchange

```
class OrderbookExchange(ExchangeOperator) [abstract]
```

Extends `ExchangeOperator` with order book management. Adds methods to subscribe to and apply live order book updates.

---

## financepype.operators.blockchains.blockchain

### BlockchainOperator

```
class BlockchainOperator(Operator) [abstract]
```

Base for blockchain network connectors. Handles transaction building, signing, broadcasting, and receipt tracking.

---

## financepype.operators.blockchains.identifier

### BlockchainIdentifier

Used as the typed identifier for blockchain transactions and assets. Represents values such as transaction hashes or contract addresses.

---

## financepype.operators.blockchains.models

Blockchain-specific data models used by `BlockchainOperator` subclasses (e.g., network configuration, gas settings).

---

## financepype.operators.dapps.dapp

### DAppOperator

```
class DAppOperator(BlockchainOperator) [abstract]
```

Extends `BlockchainOperator` for decentralized application interactions. Adds smart contract interaction methods.

---

## financepype.operators.factory

### OperatorFactory

```
class OperatorFactory
```

Registry for creating and retrieving operator instances.

**Class Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(identifier: str, factory: Callable) -> None` | Register a factory function |
| `get` | `(identifier: str) -> Operator` | Retrieve or create an operator |

---

## financepype.operators.nonce_creator

### NonceCreator

Generates unique, monotonically increasing integer nonces for use as client operation identifiers.

```python
from financepype.operators.nonce_creator import NonceCreator

creator = NonceCreator.for_microseconds()
nonce = creator.get_tracking_nonce()  # e.g., 1700000000123456
```

Each call returns a value strictly greater than the previous call (within the same process).
