# FinancePype

**FinancePype** is a Python library for building trading systems that operate across centralized and decentralized exchanges. It provides a unified abstraction layer over platforms, assets, orders, transactions, and account management, enabling consistent trading logic regardless of the underlying venue.

The library is inspired by concepts from [hummingbot](https://github.com/hummingbot/hummingbot), with an emphasis on simplicity, modularity, and strong typing via Pydantic.

---

## Features

**Multi-Platform Support**

Seamlessly work with centralized exchanges (CEX) and decentralized exchanges or protocols (DEX/DApp) through a unified interface.

**Asset Management**

- Spot assets with symbol-based identification
- Derivative contracts (futures, perpetuals, options) with side tracking
- Blockchain assets with decimal conversion utilities
- Global asset factory with caching for consistent identity

**Market Data**

- Candlestick data with timeframe aggregation and gap-filling
- Order book management with snapshot and differential updates
- Funding rate information for perpetual markets
- Borrow and staking rate tracking
- Derivative position management

**Order Management**

- Market and limit orders with full lifecycle tracking
- Order modifiers: Post-Only, Reduce-Only, IOC, FOK
- Trade fill tracking with average price calculation
- Async waiting for exchange confirmations

**Transaction Management**

- Full blockchain transaction lifecycle (pending, broadcast, confirm, finalize)
- Transaction receipt processing
- Support for cancel and speed-up operations

**Trading Rules Engine**

- Per-pair constraints: min/max size, price tick, notional limits
- Order type and modifier support validation
- Derivative rules with expiry and start-time awareness

**Balance Simulation**

- Four-phase cashflow simulation (opening/closing inflows and outflows)
- Engines for spot, perpetual, option, funding, borrow, staking, and multi-engine scenarios
- Balance tracker with locking, freezing, and history support

**Secret Management**

- Local JSON file backend for development
- AWS Secrets Manager backend for production

---

## Installation

FinancePype requires Python 3.13 or later.

```bash
pip install financepype
```

With [uv](https://github.com/astral-sh/uv):

```bash
uv add financepype
```

---

## Quick Example

```python
from decimal import Decimal
from financepype.platforms.platform import Platform
from financepype.assets.factory import AssetFactory
from financepype.markets.trading_pair import TradingPair
from financepype.rules.trading_rule import TradingRule

# Define a platform
binance = Platform(identifier="binance")

# Create assets via the factory (cached singletons)
btc = AssetFactory.get_asset(binance, "BTC")
usdt = AssetFactory.get_asset(binance, "USDT")

# Create a trading pair
btc_usdt = TradingPair(name="BTC-USDT")
print(btc_usdt.base)   # BTC
print(btc_usdt.quote)  # USDT

# Define trading rules
rule = TradingRule(
    trading_pair=btc_usdt,
    min_order_size=Decimal("0.001"),
    min_price_increment=Decimal("0.01"),
    min_notional_size=Decimal("10"),
)
print(rule.supports_limit_orders)  # True
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic >= 2.10` | Data validation and immutable models |
| `eventspype >= 1.1` | Event publication and subscription |
| `chronopype >= 0.6` | Clock and timing primitives |
| `cachetools >= 4.2` | TTL caching for operation tracking |
| `boto3 >= 1.35` | AWS Secrets Manager integration |
| `pandas >= 2.2` | Market data loading (optional for Parquet) |
| `bidict >= 0.23` | Bidirectional symbol mapping |
| `sortedcontainers >= 2.4` | Sorted collections for order book |

---

## Project Links

- **Source Code**: [github.com/gianlucapagliara/financepype](https://github.com/gianlucapagliara/financepype)
- **Issue Tracker**: [GitHub Issues](https://github.com/gianlucapagliara/financepype/issues)
- **License**: [MIT](https://github.com/gianlucapagliara/financepype/blob/main/LICENSE)
