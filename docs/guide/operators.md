# Operators

Operators are the connection layer between FinancePype's abstract model and a concrete trading venue — a centralized exchange, a blockchain, or a decentralized application. Each operator wraps a `Platform` and provides the runtime machinery for fetching data, submitting operations, and tracking state.

## Operator (Base Class)

`Operator` is the root class for all connectors.

```python
from financepype.operators.operator import Operator, OperatorConfiguration
from financepype.platforms.platform import Platform

config = OperatorConfiguration(platform=Platform(identifier="binance"))
```

Key attributes provided by `Operator`:

| Attribute | Description |
|-----------|-------------|
| `platform` | The `Platform` this operator connects to |
| `name` | String identifier (delegates to `platform.identifier`) |
| `display_name` | Human-readable name (same as `name` by default) |
| `publishing` | `MultiPublisher` for broadcasting events |
| `current_timestamp` | Abstract — subclasses return the current exchange time |

`Operator` also creates a `NonceCreator` on init that generates microsecond-precision unique integers for use as client operation IDs.

## OperatorProcessor

`OperatorProcessor` extends `chronopype.NetworkProcessor` and adds a polling loop pattern suitable for exchange REST API connectors.

```python
from financepype.operators.operator import OperatorProcessor

class MyExchangeProcessor(OperatorProcessor):
    async def _update_loop_fetch_updates(self) -> None:
        # called every time the poll_notifier fires
        updates = await self._operator.fetch_updates()
        for update in updates:
            ...
```

The processor:

- Waits on `_poll_notifier` (an `asyncio.Event`) before each poll
- Calls `_update_loop_fetch_updates()` (abstract)
- Resets the notifier and records the timestamp
- Sleeps 0.5 s on unexpected errors and retries

## NonceCreator

`NonceCreator` generates monotonically increasing integers for client operation IDs.

```python
from financepype.operators.nonce_creator import NonceCreator

nonce = NonceCreator.for_microseconds()
print(nonce.get_tracking_nonce())  # e.g. 1700000000123456
```

## Exchange Operators

### ExchangeOperator

`ExchangeOperator` extends `Operator` for centralized exchange connections. It is the base class for all CEX adapters and adds order management and trading rules tracking.

```python
from financepype.operators.exchanges.exchange import ExchangeOperator
```

Subclasses implement:

- Order placement, cancellation, and status queries
- Balance fetching
- Trading rules updates
- WebSocket stream subscriptions

### OrderbookExchange

`OrderbookExchange` extends `ExchangeOperator` to add order book management, providing methods to subscribe to and maintain live order book state.

## Blockchain Operators

### BlockchainOperator

`BlockchainOperator` extends `Operator` for blockchain network connections. It handles:

- Transaction building and signing
- Transaction broadcasting
- Receipt polling and confirmation tracking
- Nonce management for the chain

```python
from financepype.operators.blockchains.blockchain import BlockchainOperator
```

### BlockchainIdentifier

`BlockchainIdentifier` represents a chain-native identifier such as a transaction hash or contract address.

```python
from financepype.operators.blockchains.identifier import BlockchainIdentifier
```

## DApp Operators

### DAppOperator

`DAppOperator` extends `BlockchainOperator` to add DApp-specific operations, such as interacting with smart contracts, managing liquidity positions, or executing swaps.

```python
from financepype.operators.dapps.dapp import DAppOperator
```

## OperatorFactory

`OperatorFactory` provides a centralised registry for creating and retrieving operator instances by platform identifier.

```python
from financepype.operators.factory import OperatorFactory

# Register a factory function for a platform
OperatorFactory.register("binance", lambda config: MyBinanceOperator(config))

# Retrieve an operator
op = OperatorFactory.get("binance")
```

## Usage Pattern

The typical flow for using an operator:

```python
import asyncio
from financepype.platforms.platform import Platform
from financepype.operators.operator import OperatorConfiguration

async def main():
    config = OperatorConfiguration(platform=Platform(identifier="binance"))
    operator = MyBinanceExchange(config)

    # Start background tasks
    loop = asyncio.get_event_loop()
    loop.create_task(operator.rules_tracker.update_loop(interval_seconds=1800))

    # Fetch balances
    await operator.update_all_balances()

    # Place an order
    order = await operator.place_order(
        trading_pair="BTC-USDT",
        order_type="LIMIT",
        trade_type="BUY",
        amount=0.01,
        price=50000,
    )
    print(order.client_operation_id)

asyncio.run(main())
```

## Event Publishing

All operators publish events through their `MultiPublisher`. Subscribers register interest in specific event types:

```python
from eventspype.sub.subscriber import EventSubscriber
from eventspype.pub.publication import EventPublication

class MyListener(EventSubscriber):
    def on_order_filled(self, event):
        print(f"Order filled: {event}")

listener = MyListener()
operator.publishing.subscribe(OrderFilledEvent, listener.on_order_filled)
```

## Integration with chronopype

Operators use `chronopype.NetworkProcessor` as the base for their update loops. This provides:

- Structured `start()` / `stop()` lifecycle
- Configurable polling intervals
- Automatic error handling and retry
- Access to `state.last_timestamp` for tracking poll times
