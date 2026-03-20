# Owners

The `owners` module models trading account holders — the entities that own balances, hold positions, and submit operations. An owner is the "who" behind every trade.

## OwnerIdentifier

`OwnerIdentifier` uniquely identifies an account on a platform. It combines the platform and a name string into a single frozen Pydantic model.

```python
from financepype.owners.owner import OwnerIdentifier
from financepype.platforms.platform import Platform

platform = Platform(identifier="binance")
owner_id = OwnerIdentifier(platform=platform, name="trader1")

print(owner_id.identifier)  # binance:trader1
print(repr(owner_id))       # <Owner: binance:trader1>

# Unknown owner (name=None)
anon = OwnerIdentifier(platform=platform, name=None)
print(anon.identifier)      # binance:unknown
```

`OwnerIdentifier` is frozen and hashable. Use it as a dict key or in sets.

## OwnerConfiguration

`OwnerConfiguration` carries the configuration required to construct an `Owner`.

```python
from financepype.owners.owner import OwnerConfiguration

config = OwnerConfiguration(identifier=owner_id)
```

## Owner (Base Class)

`Owner` is the abstract base for all account types. It extends `eventspype.MultiPublisher`, meaning owners can publish events (e.g., balance change notifications).

```python
from financepype.owners.owner import Owner, OwnerConfiguration
```

Each `Owner` initialises:

- A `BalanceTracker` instance for managing asset balances
- An `asyncio.Event` (`_balances_ready`) that signals when the initial balance snapshot is complete

### Balance Management

```python
# Get balances
btc_balance = owner.get_balance("BTC")           # total balance
btc_available = owner.get_available_balance("BTC")  # available balance

all_total = owner.get_all_balances()        # dict[str, Decimal]
all_avail = owner.get_all_available_balances()  # dict[str, Decimal]

# Set balances from exchange snapshot
from financepype.assets.factory import AssetFactory
btc = AssetFactory.get_asset(owner.platform, "BTC")
usdt = AssetFactory.get_asset(owner.platform, "USDT")

owner.set_balances(
    total_balances=[(btc, Decimal("1.5")), (usdt, Decimal("50000"))],
    available_balances=[(btc, Decimal("1.0")), (usdt, Decimal("45000"))],
    complete_snapshot=True,  # zero out assets not in the list
)
```

### Position Management

```python
from financepype.assets.contract import DerivativeSide

# Get a position
pos = owner.get_position("BTC-USDT-PERPETUAL", DerivativeSide.LONG)

# Get all positions
all_positions = owner.get_all_positions()  # dict[DerivativeContract, Position]

# Set a position (from exchange snapshot)
owner.set_position(position)

# Remove a position (when closed)
from financepype.markets.trading_pair import TradingPair
owner.remove_position(TradingPair(name="BTC-USDT-PERPETUAL"), DerivativeSide.LONG)
```

### Abstract Methods

Subclasses must implement:

```python
@property
@abstractmethod
def current_timestamp(self) -> float: ...

@abstractmethod
async def update_all_balances(self) -> None: ...

@abstractmethod
async def update_all_positions(self) -> None: ...

@abstractmethod
async def update_balance(self, asset: Asset) -> None: ...
```

## Concrete Owner Types

### Account

`Account` extends `Owner` for centralized exchange accounts. It typically wraps an `ExchangeOperator` and delegates balance and position queries to it.

### Wallet

`Wallet` extends `Owner` for blockchain wallets. It wraps a `BlockchainOperator` and handles on-chain balance queries and transaction signing.

## MultiOwner

`MultiOwner` aggregates multiple `Owner` instances and provides a unified view of balances and positions across all of them.

```python
from financepype.owners.multiowner import MultiOwner
```

`MultiOwner` is useful when a trading strategy operates across several accounts on different exchanges simultaneously.

## OwnerFactory

`OwnerFactory` is a registry for creating owner instances by identifier.

```python
from financepype.owners.factory import OwnerFactory

OwnerFactory.register("binance:trader1", lambda config: MyAccount(config))
owner = OwnerFactory.get("binance:trader1")
```

## Example: Setting Up an Owner

```python
import asyncio
from decimal import Decimal
from financepype.platforms.platform import Platform
from financepype.owners.owner import OwnerIdentifier, OwnerConfiguration

platform = Platform(identifier="binance")
owner_id = OwnerIdentifier(platform=platform, name="main")
config = OwnerConfiguration(identifier=owner_id)

# Subclass Owner for your exchange
class BinanceAccount(Owner):
    def __init__(self, config, operator):
        super().__init__(config)
        self._operator = operator

    @property
    def current_timestamp(self):
        return self._operator.current_timestamp

    async def update_all_balances(self):
        balances = await self._operator.fetch_balances()
        self.set_balances(
            total_balances=balances["total"],
            available_balances=balances["available"],
            complete_snapshot=True,
        )

    async def update_all_positions(self):
        positions = await self._operator.fetch_positions()
        for pos in positions:
            self.set_position(pos)

    async def update_balance(self, asset):
        amount = await self._operator.fetch_balance(asset)
        self.set_balances(
            total_balances=[(asset, amount["total"])],
            available_balances=[(asset, amount["available"])],
        )
```

## BalanceTracker Integration

`Owner` delegates all balance storage to a `BalanceTracker`. The tracker handles:

- Total vs. available balance separation
- Balance locking for open orders
- Optional history tracking

See the [Simulations guide](simulations.md) for detailed `BalanceTracker` documentation.
