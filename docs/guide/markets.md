# Markets

The `markets` module provides data models for all market-related information: instrument metadata, candlestick data, trade records, order books, positions, and funding/lending rates.

## Trading Pairs and Market Info

### TradingPair

`TradingPair` is a singleton Pydantic model identified by its name string. The name follows the pattern `BASE-QUOTE[-TYPE[-TIMEFRAME-EXPIRY[-STRIKE]]]`.

```python
from financepype.markets.trading_pair import TradingPair

# Spot pair
spot = TradingPair(name="BTC-USDT")
print(spot.base)         # BTC
print(spot.quote)        # USDT

# Perpetual contract
perp = TradingPair(name="BTC-USDT-PERPETUAL")
print(perp.market_type)  # MarketType.PERPETUAL
print(perp.market_info.is_perpetual)  # True

# Weekly future expiring 2026-01-01
future = TradingPair(name="BTC-USDT-FUTURE-1W-20260101")
print(future.market_info.is_future)      # True
print(future.market_info.expiry_date)    # datetime(2026, 1, 1)
print(future.market_info.timeframe_type) # MarketTimeframe.WEEKLY
```

Singleton behaviour: the same name always returns the same object.

```python
a = TradingPair(name="BTC-USDT")
b = TradingPair(name="BTC-USDT")
assert a is b
```

### MarketType

`MarketType` categorises instruments:

| Value | Description |
|-------|-------------|
| `SPOT` | Spot trading |
| `FUTURE` | Linear futures |
| `INVERSE_FUTURE` | Inverse futures |
| `PERPETUAL` | Linear perpetual |
| `INVERSE_PERPETUAL` | Inverse perpetual |
| `EQUITY` | Equity (treated as perpetual) |
| `CALL_OPTION` | Call option |
| `PUT_OPTION` | Put option |
| `INVERSE_CALL_OPTION` | Inverse call option |
| `INVERSE_PUT_OPTION` | Inverse put option |
| `CALL_SPREAD` | Call spread |
| `PUT_SPREAD` | Put spread |
| `VOLATILITY` | Volatility instrument |

Useful boolean properties on `MarketType`:

```python
from financepype.markets.market import MarketType

t = MarketType.PERPETUAL
print(t.is_spot)        # False
print(t.is_derivative)  # True
print(t.is_perpetual)   # True
print(t.is_future)      # False
print(t.is_option)      # False
print(t.is_linear)      # True
print(t.is_inverse)     # False
```

### MarketInfo

`MarketInfo` contains fully parsed instrument metadata. It is returned by `TradingPair.market_info` and by `MarketInfo.split_client_instrument_name()`.

```python
from financepype.markets.market import MarketInfo, MarketType

# Parse directly
info = MarketInfo.split_client_instrument_name("ETH-USDT-PERPETUAL")
print(info.base)        # ETH
print(info.quote)       # USDT
print(info.market_type) # MarketType.PERPETUAL

# Reconstruct client name
print(info.client_name) # ETH-USDT-PERPETUAL
```

For options, `strike_price` and `expiry_date` are required:

```python
info = MarketInfo.split_client_instrument_name("BTC-USDT-CALL_OPTION-1W-20260101-50000")
print(info.strike_price)  # Decimal('50000')
```

### MarketTimeframe

`MarketTimeframe` represents standard contract durations:

`1H`, `2H`, `4H`, `1D`, `2D`, `1W`, `2W`, `1M`, `2M`, `1Q`, `2Q`, `1Y`, `NA`

## Candlestick Data

### Candle

`Candle` is an OHLCV record for a time period.

```python
from datetime import datetime, timedelta
from decimal import Decimal
from financepype.markets.candle import Candle, CandleTimeframe, CandleType

candle = Candle(
    start_time=datetime(2026, 1, 1, 0, 0),
    end_time=datetime(2026, 1, 1, 1, 0),
    open=Decimal("50000"),
    close=Decimal("51000"),
    high=Decimal("51500"),
    low=Decimal("49800"),
    volume=Decimal("123.45"),
)
```

**Gap filling** — produce a continuous series by propagating the previous close:

```python
start = datetime(2026, 1, 1)
end = datetime(2026, 1, 2)
filled = Candle.fill_missing_candles_with_prev_candle(candles, start, end)
```

**Interval conversion** — aggregate 1-hour candles into 4-hour candles:

```python
four_hour = Candle.convert_candles_interval(hourly_candles, seconds_interval=14400)
```

### CandleTimeframe

Pre-defined second values for standard intervals:

```
SEC_1=1, MIN_1=60, MIN_5=300, MIN_15=900, MIN_30=1800,
HOUR_1=3600, HOUR_2=7200, HOUR_4=14400,
DAY_1=86400, WEEK_1=604800, MONTH_1=2592000
```

### CandleType

`PRICE`, `MARK`, `INDEX`, `PREMIUM`, `FUNDING`, `ACCRUED_FUNDING`

## Trades

### PublicTrade

Represents a single public trade visible on the market feed.

```python
from datetime import datetime
from decimal import Decimal
from financepype.markets.trade import PublicTrade
from financepype.markets.trading_pair import TradingPair
from financepype.operations.orders.models import TradeType

trade = PublicTrade(
    trade_id="t001",
    trading_pair=TradingPair(name="BTC-USDT"),
    price=Decimal("50000"),
    amount=Decimal("0.1"),
    side=TradeType.BUY,
    time=datetime.now(),
    is_liquidation=False,
)
```

## Order Book

The order book implementation uses float internally for performance, with `Decimal` conversions for client-facing APIs.

### Key Data Classes

| Class | Description |
|-------|-------------|
| `OrderBookEntry` | A single price level: price, amount, update_id |
| `OrderBookRow` | Internal row used when applying updates (float) |
| `ClientOrderBookRow` | External row with Decimal values |
| `OrderBookQueryResult` | Result of a price/volume query (float) |
| `ClientOrderBookQueryResult` | Same with Decimal values |

### Order Book Messages

| Class | Type | Description |
|-------|------|-------------|
| `OrderBookUpdateMessage` | SNAPSHOT / DIFF | Full or incremental book update |
| `OrderBookTradeMessage` | TRADE | A trade event |

```python
from financepype.markets.orderbook.models import (
    OrderBookUpdateMessage, OrderBookMessageType, OrderBookTradeMessage
)
from financepype.markets.trading_pair import TradingPair

pair = TradingPair(name="BTC-USDT")
snapshot = OrderBookUpdateMessage(
    type=OrderBookMessageType.SNAPSHOT,
    timestamp=1700000000.0,
    trading_pair=pair,
    update_id=1,
    raw_asks=[(50100.0, 0.5), (50200.0, 1.0)],
    raw_bids=[(49900.0, 0.3), (49800.0, 2.0)],
)
print(snapshot.asks[0])  # OrderBookRow(price=50100.0, amount=0.5, update_id=1)
```

### OrderBookEvent

Events emitted by the order book:

- `TradeEvent` — a trade occurred
- `OrderBookUpdateEvent` — the book state changed

## Positions

### Position

`Position` models an open derivative position.

```python
from decimal import Decimal
from financepype.markets.position import Position
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.assets.asset_id import AssetIdentifier
from financepype.platforms.platform import Platform

platform = Platform(identifier="binance")
asset = DerivativeContract(
    platform=platform,
    identifier=AssetIdentifier(value="BTC-USDT-PERPETUAL"),
    side=DerivativeSide.LONG,
)

position = Position(
    asset=asset,
    amount=Decimal("0.1"),
    leverage=Decimal("10"),
    entry_price=Decimal("50000"),
    entry_index_price=Decimal("49990"),
    margin=Decimal("500"),
    unrealized_pnl=Decimal("100"),
    liquidation_price=Decimal("45000"),
)

print(position.is_long)          # True
print(position.value)            # Decimal('5000')  (entry_price * amount)
print(position.unrealized_percentage_pnl)  # Decimal('20') %

# Distance from liquidation
print(position.distance_from_liquidation(Decimal("50000")))  # 5000
```

## Funding Rates

### FundingInfo

`FundingInfo` holds the current funding state for a perpetual market.

```python
from decimal import Decimal
from financepype.markets.funding import FundingInfo, FundingPaymentType
from financepype.markets.trading_pair import TradingPair

info = FundingInfo(
    trading_pair=TradingPair(name="BTC-USDT-PERPETUAL"),
    index_price=Decimal("50000"),
    mark_price=Decimal("50100"),
    next_funding_utc_timestamp=1700028800,
    next_funding_rate=Decimal("0.01"),
    last_funding_utc_timestamp=1700000000,
    last_funding_rate=Decimal("0.008"),
    payment_type=FundingPaymentType.NEXT,
)

print(info.payment_seconds_interval)   # 28800 (8 hours)
print(info.has_live_payments)          # False

# Project future payments
rates = info.get_next_payment_rates()
```

### FundingPayment

Records an actual funding payment that was received or paid.

### FundingInfoUpdate

A partial update to apply to an existing `FundingInfo` via `info.update(update)`.

## Borrow and Staking Rates

The `rates` module mirrors the funding structure but for lending (borrow rates) and staking rewards.

### BorrowInfo / StakingInfo

```python
from financepype.markets.rates import BorrowInfo, RatePaymentType
from financepype.assets.factory import AssetFactory
from financepype.platforms.platform import Platform
from decimal import Decimal

platform = Platform(identifier="binance")
usdt = AssetFactory.get_asset(platform, "USDT")

borrow = BorrowInfo(
    asset=usdt,
    current_rate=Decimal("5.0"),   # 5% APR
    next_payment_utc_timestamp=1700028800,
    next_rate=Decimal("5.1"),
    last_payment_utc_timestamp=1700000000,
    last_rate=Decimal("4.9"),
    payment_type=RatePaymentType.NEXT,
)

print(borrow.payment_seconds_interval)  # 28800
```

Both classes expose `update(info_update)` and `get_next_payment_rates()` with the same signatures as `FundingInfo`.

## Lending Positions

The `lending` module provides position models for borrow and staking positions — representing the ongoing state, not the operations that created them.

### BorrowPosition

```python
from financepype.markets.lending import BorrowPosition
from decimal import Decimal

pos = BorrowPosition(
    borrowed_asset=usdt,
    collateral_asset=btc,
    borrowed_amount=Decimal("10000"),
    collateral_amount=Decimal("0.25"),
    interest_rate=Decimal("5.0"),
    entry_timestamp=1700000000,
    liquidation_threshold=Decimal("80"),
)

print(pos.total_debt)        # borrowed_amount + accrued_interest
print(pos.collateral_ratio)  # percentage
print(pos.is_at_liquidation_risk(
    collateral_price=Decimal("50000"),
    borrowed_price=Decimal("1"),
))
```

### StakingPosition

Similar to `BorrowPosition` but tracks staked amount and reward accrual:

```python
from financepype.markets.lending import StakingPosition

staking = StakingPosition(
    staked_asset=btc,
    reward_asset=btc,
    staked_amount=Decimal("1.0"),
    reward_rate=Decimal("3.0"),  # 3% APY
    entry_timestamp=1700000000,
)
rewards = staking.calculate_rewards_for_period(1700000000, 1731536000)
```
