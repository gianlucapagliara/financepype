# Trading Rules

The `rules` module enforces exchange constraints on trading operations. Every trading pair on every exchange has a set of rules that determine what orders are valid.

## TradingRule

`TradingRule` is a Pydantic model that captures the constraints for a single trading pair.

```python
from decimal import Decimal
from financepype.markets.trading_pair import TradingPair
from financepype.rules.trading_rule import TradingRule
from financepype.operations.orders.models import OrderType, OrderModifier

rule = TradingRule(
    trading_pair=TradingPair(name="BTC-USDT"),
    min_order_size=Decimal("0.001"),
    max_order_size=Decimal("100"),
    min_price_increment=Decimal("0.01"),
    min_base_amount_increment=Decimal("0.00001"),
    min_quote_amount_increment=Decimal("0.01"),
    min_notional_size=Decimal("10"),
    max_notional_size=Decimal("1000000"),
    supported_order_types={OrderType.LIMIT, OrderType.MARKET},
    supported_order_modifiers={OrderModifier.POST_ONLY, OrderModifier.REDUCE_ONLY},
    is_live=True,
)
```

### Fields

| Field | Default | Description |
|-------|---------|-------------|
| `trading_pair` | required | The pair these rules apply to |
| `min_order_size` | `0` | Minimum size in base currency |
| `max_order_size` | `1e20` | Maximum size in base currency |
| `min_price_increment` | `1e-20` | Tick size (price step) |
| `min_price_significance` | `0` | Minimum significant price digits |
| `min_base_amount_increment` | `1e-20` | Size step for base currency |
| `min_quote_amount_increment` | `1e-20` | Size step for quote currency |
| `min_notional_size` | `0` | Minimum order value in quote |
| `max_notional_size` | `1e20` | Maximum order value in quote |
| `supported_order_types` | `{LIMIT, MARKET}` | Allowed order types |
| `supported_order_modifiers` | `{POST_ONLY}` | Allowed order modifiers |
| `buy_order_collateral_token` | `quote currency` | Collateral for buy orders |
| `sell_order_collateral_token` | `base currency` | Collateral for sell orders |
| `product_id` | `None` | Exchange-specific product ID |
| `is_live` | `True` | Whether trading is enabled |
| `other_rules` | `{}` | Extra exchange-specific constraints |

### Properties

```python
rule.supports_limit_orders    # True if LIMIT in supported_order_types
rule.supports_market_orders   # True if MARKET in supported_order_types
rule.active                   # is_active() with no timestamp
rule.started                  # is_started() with no timestamp
rule.expired                  # is_expired() with no timestamp
```

### Lifecycle Methods

For spot rules, these always return the same static values:

```python
rule.is_active()     # True (always active for spot)
rule.is_started()    # True (always started for spot)
rule.is_expired()    # False (never expires for spot)
```

Pass a timestamp to check at a specific point in time (used mainly for derivatives):

```python
rule.is_active(timestamp=1700000000)
```

### Collateral Token Defaults

If `buy_order_collateral_token` or `sell_order_collateral_token` are not specified, they are set automatically:

- Buy orders: collateral = **quote** currency
- Sell orders: collateral = **base** currency

```python
rule = TradingRule(trading_pair=TradingPair(name="BTC-USDT"))
print(rule.buy_order_collateral_token)   # USDT
print(rule.sell_order_collateral_token)  # BTC
```

## DerivativeTradingRule

`DerivativeTradingRule` extends `TradingRule` with derivative-specific attributes.

```python
from financepype.rules.trading_rule import DerivativeTradingRule

# Perpetual contract (expiry_timestamp = -1)
perp_rule = DerivativeTradingRule(
    trading_pair=TradingPair(name="BTC-USDT-PERPETUAL"),
    expiry_timestamp=-1,
    underlying="BTC",
    index_symbol="BTC/USD",
)
print(perp_rule.perpetual)     # True
print(perp_rule.is_expired())  # False

# Expiring future
future_rule = DerivativeTradingRule(
    trading_pair=TradingPair(name="BTC-USDT-FUTURE-1W-20260101"),
    expiry_timestamp=1767225600.0,  # 2026-01-01 00:00 UTC
    start_timestamp=1764547200.0,
    underlying="BTC",
)
print(future_rule.perpetual)           # False
print(future_rule.is_active())         # depends on current time
print(future_rule.is_expired(1800000000))  # True (past expiry)
```

### Additional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `underlying` | `None` | Underlying asset symbol |
| `strike_price` | `None` | Strike price for options |
| `start_timestamp` | `0` | When trading begins |
| `expiry_timestamp` | `-1` | When trading ends (−1 = perpetual) |
| `index_symbol` | `None` | Index being tracked |

### Collateral for Derivatives

Collateral is automatically set based on linear/inverse classification:

- **Linear** (PERPETUAL, FUTURE): collateral = **quote** for both sides
- **Inverse** (INVERSE_PERPETUAL, INVERSE_FUTURE): collateral = **base** for both sides

## TradingRulesTracker

`TradingRulesTracker` is an abstract class that manages a live set of rules for an exchange. It maintains a bidirectional mapping between exchange-native symbols and standardized `TradingPair` names.

```python
from financepype.rules.trading_rules_tracker import TradingRulesTracker
from bidict import bidict

class BinanceRulesTracker(TradingRulesTracker):
    async def update_trading_rules(self) -> None:
        # Fetch from exchange API
        raw_rules = await self.exchange.get_exchange_info()

        rules = {}
        symbol_map = bidict()
        for item in raw_rules["symbols"]:
            pair = TradingPair(name=f"{item['baseAsset']}-{item['quoteAsset']}")
            rule = TradingRule(
                trading_pair=pair,
                min_order_size=Decimal(item["minQty"]),
                min_price_increment=Decimal(item["tickSize"]),
            )
            rules[pair] = rule
            symbol_map[pair] = item["symbol"]

        self.set_trading_rules(rules)
        self.set_trading_pair_symbol_map(symbol_map)
```

### Usage

```python
tracker = BinanceRulesTracker()
await tracker.update_trading_rules()

# Check readiness
print(tracker.is_ready)   # True after first successful update
print(tracker.is_locked)  # True while updating

# Query
all_pairs = await tracker.all_trading_pairs()
exchange_sym = await tracker.exchange_symbol_associated_to_pair(
    TradingPair(name="BTC-USDT")
)  # e.g. "BTCUSDT"

std_pair = await tracker.trading_pair_associated_to_exchange_symbol("BTCUSDT")

# Validation
valid = await tracker.is_trading_pair_valid(TradingPair(name="BTC-USDT"))
```

### Background Update Loop

```python
import asyncio

async def main():
    tracker = BinanceRulesTracker()
    # Update every 30 minutes
    task = asyncio.create_task(tracker.update_loop(interval_seconds=1800))
    ...

asyncio.run(main())
```

### Direct Rule Access

```python
rules = tracker.trading_rules  # dict[TradingPair, TradingRule]
btc_rule = rules.get(TradingPair(name="BTC-USDT"))

# Update individual rule
tracker.set_trading_rule(TradingPair(name="ETH-USDT"), new_rule)

# Remove a rule
tracker.remove_trading_rule(TradingPair(name="DOGE-USDT"))
```
