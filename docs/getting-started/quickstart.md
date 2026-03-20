# Quick Start

This guide walks through the core building blocks of FinancePype with short, self-contained examples. Each section can be read independently.

## Platforms

A `Platform` represents an exchange or blockchain. Platforms are cached singletons — the same identifier always returns the same instance.

```python
from financepype.platforms.platform import Platform
from financepype.platforms.centralized import CentralizedPlatform

# Simple platform (base class)
binance = Platform(identifier="binance")
kraken = Platform(identifier="kraken")

# Re-using the same identifier returns the same object
binance2 = Platform(identifier="binance")
assert binance is binance2

# Centralized platform with optional sub-account and domain
okx = CentralizedPlatform(identifier="okx", sub_identifier="main", domain="okx.com")
```

## Assets

Assets represent tradable instruments. The `AssetFactory` creates and caches asset instances.

```python
from financepype.platforms.platform import Platform
from financepype.assets.factory import AssetFactory
from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.spot import SpotAsset

platform = Platform(identifier="binance")

# Create a spot asset via the factory
btc = AssetFactory.get_asset(platform, "BTC")
usdt = AssetFactory.get_asset(platform, "USDT")
print(btc.identifier)  # AssetIdentifier(value='BTC')

# Assets are cached — same call returns the same instance
btc2 = AssetFactory.get_asset(platform, "BTC")
assert btc is btc2

# Create directly
eth = SpotAsset(
    platform=platform,
    identifier=AssetIdentifier(value="ETH"),
    name="Ethereum",
)
print(eth.symbol)  # ETH
print(eth.name)    # Ethereum
```

## Trading Pairs

`TradingPair` parses and validates instrument names. Like platforms, they are singletons.

```python
from financepype.markets.trading_pair import TradingPair
from financepype.markets.market import MarketType

# Spot pair
btc_usdt = TradingPair(name="BTC-USDT")
print(btc_usdt.base)        # BTC
print(btc_usdt.quote)       # USDT
print(btc_usdt.market_type) # MarketType.SPOT

# Perpetual pair
btc_perp = TradingPair(name="BTC-USDT-PERPETUAL")
print(btc_perp.market_type)              # MarketType.PERPETUAL
print(btc_perp.market_info.is_perpetual) # True

# Future pair (requires timeframe and expiry)
future = TradingPair(name="BTC-USDT-FUTURE-1W-20260101")
print(future.market_info.is_future)      # True
print(future.market_info.expiry_date)    # datetime(2026, 1, 1)
```

## Trading Rules

`TradingRule` enforces exchange constraints on orders.

```python
from decimal import Decimal
from financepype.markets.trading_pair import TradingPair
from financepype.rules.trading_rule import TradingRule, DerivativeTradingRule
from financepype.operations.orders.models import OrderType, OrderModifier

pair = TradingPair(name="BTC-USDT")

rule = TradingRule(
    trading_pair=pair,
    min_order_size=Decimal("0.001"),
    max_order_size=Decimal("1000"),
    min_price_increment=Decimal("0.01"),
    min_notional_size=Decimal("10"),
    supported_order_types={OrderType.LIMIT, OrderType.MARKET},
    supported_order_modifiers={OrderModifier.POST_ONLY, OrderModifier.REDUCE_ONLY},
)

print(rule.supports_limit_orders)   # True
print(rule.supports_market_orders)  # True
print(rule.active)                  # True
print(rule.buy_order_collateral_token)   # USDT (auto-set from quote)
print(rule.sell_order_collateral_token)  # BTC (auto-set from base)

# Derivative rule with expiry
perp_rule = DerivativeTradingRule(
    trading_pair=TradingPair(name="BTC-USDT-PERPETUAL"),
    expiry_timestamp=-1,  # -1 means perpetual (no expiry)
    underlying="BTC",
)
print(perp_rule.perpetual)    # True
print(perp_rule.is_expired()) # False
```

## Orders

`OrderOperation` tracks a trading order through its lifecycle.

```python
import time
from decimal import Decimal
from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.order import OrderOperation
from financepype.operations.orders.models import (
    OrderType, TradeType, OrderState, OrderUpdate, TradeUpdate,
)
from financepype.operations.fees import OperationFee, FeeType, FeeImpactType
from financepype.owners.owner import OwnerIdentifier
from financepype.platforms.platform import Platform

platform = Platform(identifier="binance")
owner_id = OwnerIdentifier(platform=platform, name="trader1")

# Create an order
order = OrderOperation(
    client_operation_id="order_001",
    owner_identifier=owner_id,
    creation_timestamp=time.time(),
    trading_pair=TradingPair(name="BTC-USDT"),
    order_type=OrderType.LIMIT,
    trade_type=TradeType.BUY,
    amount=Decimal("0.01"),
    price=Decimal("50000"),
)

print(order.current_state)    # OrderState.PENDING_CREATE
print(order.is_open)          # True

# Simulate receiving confirmation from exchange
order_update = OrderUpdate(
    trading_pair=TradingPair(name="BTC-USDT"),
    update_timestamp=time.time(),
    new_state=OrderState.OPEN,
    client_order_id="order_001",
    exchange_order_id="exch_12345",
)
order.process_operation_update(order_update)
print(order.current_state)           # OrderState.OPEN
print(order.exchange_order_id)       # exch_12345

# Simulate a partial fill
from financepype.assets.spot import SpotAsset
from financepype.assets.asset_id import AssetIdentifier

usdt_asset = SpotAsset(platform=platform, identifier=AssetIdentifier(value="USDT"))
fee = OperationFee(
    amount=Decimal("0.1"),
    asset=usdt_asset,
    fee_type=FeeType.PERCENTAGE,
    impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS,
)
trade = TradeUpdate(
    trade_id="trade_001",
    exchange_order_id="exch_12345",
    trading_pair=TradingPair(name="BTC-USDT"),
    trade_type=TradeType.BUY,
    fill_timestamp=time.time(),
    fill_price=Decimal("50000"),
    fill_base_amount=Decimal("0.01"),
    fill_quote_amount=Decimal("500"),
    fee=fee,
)
order.process_operation_update(trade)
print(order.current_state)         # OrderState.FILLED
print(order.executed_amount_base)  # 0.01
print(order.average_executed_price) # Decimal('50000')
```

## Balance Tracking

`BalanceTracker` maintains total and available balances for an account.

```python
from decimal import Decimal
from financepype.platforms.platform import Platform
from financepype.assets.factory import AssetFactory
from financepype.simulations.balances.tracking.tracker import BalanceTracker, BalanceType
from financepype.simulations.balances.tracking.lock import BalanceLock

platform = Platform(identifier="binance")
btc = AssetFactory.get_asset(platform, "BTC")
usdt = AssetFactory.get_asset(platform, "USDT")

tracker = BalanceTracker(track_history=True)

# Set initial balances
tracker.set_balance(btc, Decimal("1.0"), "initial deposit", BalanceType.TOTAL)
tracker.set_balance(btc, Decimal("1.0"), "initial deposit", BalanceType.AVAILABLE)
tracker.set_balance(usdt, Decimal("50000"), "initial deposit", BalanceType.TOTAL)
tracker.set_balance(usdt, Decimal("50000"), "initial deposit", BalanceType.AVAILABLE)

# Query balances
print(tracker.get_balance(btc, BalanceType.TOTAL))      # Decimal('1.0')
print(tracker.get_balance(usdt, BalanceType.AVAILABLE)) # Decimal('50000')

# Lock balance for an order
lock = BalanceLock(asset=usdt, amount=Decimal("500"), purpose="order_001")
tracker.lock_balance(lock)

# Unlocked (free to use minus locks)
print(tracker.get_unlocked_balance(usdt))  # Decimal('49500')
```

## Secret Management

```python
from financepype.secrets.local import LocalExchangeSecrets

# Load secrets from a local JSON file (useful during development)
secrets = LocalExchangeSecrets(file_path="/path/to/secrets.json")
exchange_secrets = secrets.update_secret("binance")
sub = exchange_secrets.get_subaccount("main")
print(sub.api_key.get_secret_value())  # your API key

# Expected JSON format:
# {
#   "exchange_secrets": {
#     "binance": {
#       "name": "binance",
#       "subaccounts": {
#         "main": {
#           "subaccount_name": "main",
#           "api_key": "...",
#           "api_secret": "..."
#         }
#       }
#     }
#   }
# }
```

## Next Steps

- Read the [User Guide](../guide/assets.md) for in-depth coverage of each module.
- Browse the [API Reference](../api/assets.md) for full class and method documentation.
