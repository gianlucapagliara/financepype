# API Reference — Markets

## financepype.markets.market

### MarketTimeframe

```
class MarketTimeframe(Enum)
```

| Value | String | Seconds |
|-------|--------|---------|
| `HOURLY` | `"1H"` | 3600 |
| `BI_HOURLY` | `"2H"` | 7200 |
| `QUART_HOURLY` | `"4H"` | 14400 |
| `DAILY` | `"1D"` | 86400 |
| `BI_DAILY` | `"2D"` | 172800 |
| `WEEKLY` | `"1W"` | 604800 |
| `BI_WEEKLY` | `"2W"` | 1209600 |
| `MONTHLY` | `"1M"` | 2678400 |
| `BI_MONTHLY` | `"2M"` | 5356800 |
| `QUARTERLY` | `"1Q"` | 7948800 |
| `BI_QUARTERLY` | `"2Q"` | 15897600 |
| `YEARLY` | `"1Y"` | 31622400 |
| `UNDEFINED` | `"NA"` | — |

### MarketType

```
class MarketType(Enum)
```

Values: `SPOT`, `FUTURE`, `INVERSE_FUTURE`, `PERPETUAL`, `INVERSE_PERPETUAL`, `EQUITY`, `CALL_OPTION`, `PUT_OPTION`, `INVERSE_CALL_OPTION`, `INVERSE_PUT_OPTION`, `CALL_SPREAD`, `PUT_SPREAD`, `VOLATILITY`

**Properties** (all `-> bool`)

| Property | True when |
|----------|-----------|
| `is_spot` | `SPOT` |
| `is_derivative` | not spot |
| `is_perpetual` | `PERPETUAL`, `INVERSE_PERPETUAL`, `EQUITY` |
| `is_future` | `FUTURE`, `INVERSE_FUTURE` |
| `is_option` | `CALL_OPTION`, `PUT_OPTION`, `INVERSE_CALL_OPTION`, `INVERSE_PUT_OPTION`, `CALL_SPREAD`, `PUT_SPREAD`, `VOLATILITY` |
| `is_inverse` | `INVERSE_FUTURE`, `INVERSE_PERPETUAL`, `INVERSE_CALL_OPTION`, `INVERSE_PUT_OPTION` |
| `is_linear` | `SPOT`, `FUTURE`, `PERPETUAL`, `EQUITY`, `CALL_OPTION`, `PUT_OPTION`, `VOLATILITY` |

### MarketInfo

```
class MarketInfo(BaseModel)
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `base` | `str` | Base currency |
| `quote` | `str` | Quote currency |
| `market_type` | `MarketType` | Instrument type |
| `timeframe_type` | `MarketTimeframe \| None` | For futures/options |
| `expiry_date` | `datetime \| None` | For futures/options |
| `strike_price` | `Decimal \| None` | For options |
| `metadata` | `dict[str, Any]` | Extra data |

**Validators** — `expiry_date` required for futures and options; `strike_price` required for options.

**Properties**

- `is_spot`, `is_derivative`, `is_perpetual`, `is_future`, `is_option`, `is_linear`, `is_inverse` → `bool`
- `client_name -> str` — reconstructs the canonical name string

**Class Methods**

- `split_client_instrument_name(name: str) -> MarketInfo` — parse `"BASE-QUOTE[-TYPE[-TF-EXPIRY[-STRIKE]]]"`
- `get_timeframe_type(launch_ts, delivery_ts, ...) -> MarketTimeframe`

---

## financepype.markets.trading_pair

### TradingPair

```
class TradingPair(BaseModel)
```

Singleton Pydantic model. The same `name` always returns the same instance.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Canonical name, e.g. `"BTC-USDT"` |

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `base` | `str` | Base currency |
| `quote` | `str` | Quote currency |
| `market_type` | `MarketType` | Instrument type |
| `market_info` | `MarketInfo` | Full parsed metadata |

**Class Methods**

- `model_validate(obj)` — handles dict deserialization

**Validators**

- `validate_name` — must contain `-` and be parseable by `MarketInfo.split_client_instrument_name`

**Special Methods**

- `__eq__` — also supports comparison with plain `str`
- `__hash__` — based on `name`
- `__deepcopy__` — returns `self` (singleton)

---

## financepype.markets.candle

### CandleTimeframe

```
class CandleTimeframe(Enum)
```

Values with their second counts: `SEC_1=1`, `MIN_1=60`, `MIN_5=300`, `MIN_15=900`, `MIN_30=1800`, `HOUR_1=3600`, `HOUR_2=7200`, `HOUR_4=14400`, `DAY_1=86400`, `WEEK_1=604800`, `MONTH_1=2592000`

### CandleType

```
class CandleType(Enum)
```

`PRICE`, `MARK`, `INDEX`, `PREMIUM`, `FUNDING`, `ACCRUED_FUNDING`

### Candle

```
class Candle(BaseModel)
```

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `start_time` | `datetime` | Candle open time |
| `end_time` | `datetime` | Candle close time |
| `open` | `Decimal` | Open price |
| `close` | `Decimal` | Close price |
| `high` | `Decimal` | High price |
| `low` | `Decimal` | Low price |
| `volume` | `Decimal \| None` | Volume (optional) |

**Class Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `fill_missing_candles_with_prev_candle` | `(candles, start, end) -> list[Candle]` | Fill gaps using previous close |
| `convert_candles_interval` | `(candles, seconds_interval) -> list[Candle]` | Aggregate to larger timeframe |

---

## financepype.markets.trade

### PublicTrade

```
class PublicTrade(BaseModel)
```

Frozen record of a public trade.

| Field | Type | Description |
|-------|------|-------------|
| `trade_id` | `str` | Unique trade ID (min length 1) |
| `trading_pair` | `TradingPair` | Market |
| `price` | `Decimal` | Execution price (must be > 0) |
| `amount` | `Decimal` | Base amount (must be > 0) |
| `side` | `TradeType` | BUY or SELL |
| `time` | `datetime` | Execution time |
| `is_liquidation` | `bool` | Was this a liquidation? |

---

## financepype.markets.orderbook.models

### OrderBookEntry

```
@dataclass class OrderBookEntry
```

| Field | Type |
|-------|------|
| `price` | `float` |
| `amount` | `float` |
| `update_id` | `int` |

Supports `<` and `==` (by price).

### OrderBookRow / ClientOrderBookRow

Internal (`float`) and external (`Decimal`) representations of an order book level.

### OrderBookMessageType

`SNAPSHOT = 1`, `DIFF = 2`, `TRADE = 3`, `FUNDING = 4`

### OrderBookEvent

`TradeEvent`, `OrderBookUpdateEvent`

### OrderBookUpdateMessage

```
@dataclass class OrderBookUpdateMessage(BaseOrderBookMessage)
```

| Field | Type | Description |
|-------|------|-------------|
| `update_id` | `int` | Sequence number |
| `first_update_id` | `int` | First ID in diff range |
| `raw_asks` | `list[tuple[float, float]]` | `(price, amount)` pairs |
| `raw_bids` | `list[tuple[float, float]]` | `(price, amount)` pairs |

**Properties**

- `asks -> list[OrderBookRow]`
- `bids -> list[OrderBookRow]`

### OrderBookTradeMessage

| Field | Type |
|-------|------|
| `trade_id` | `int` |
| `price` | `float` |
| `amount` | `float` |
| `trade_type` | `TradeType` |

---

## financepype.markets.position

### Position

```
class Position(BaseModel)
```

**Fields**

| Field | Type | Constraint |
|-------|------|------------|
| `asset` | `DerivativeContract` | |
| `amount` | `Decimal` | `> 0` |
| `leverage` | `Decimal` | `> 0` |
| `entry_price` | `Decimal` | `> 0` |
| `entry_index_price` | `Decimal` | `> 0` |
| `margin` | `Decimal` | `>= 0` |
| `unrealized_pnl` | `Decimal` | allows inf/NaN |
| `liquidation_price` | `Decimal` | `>= 0` |

**Properties**

| Property | Type | Description |
|----------|------|-------------|
| `unrealized_percentage_pnl` | `Decimal` | `unrealized_pnl / margin * 100` |
| `value` | `Decimal` | `entry_price * amount` |
| `position_side` | `DerivativeSide` | from `asset.side` |
| `is_long` | `bool` | side == LONG |
| `is_short` | `bool` | side == SHORT |

**Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `distance_from_liquidation` | `(price: Decimal) -> Decimal` | Absolute price distance from liq |
| `percentage_from_liquidation` | `(price: Decimal) -> Decimal` | Relative distance |
| `margin_distance_from_liquidation` | `(price: Decimal) -> Decimal` | Remaining margin |
| `margin_percentage_from_liquidation` | `(price: Decimal) -> Decimal` | Margin remaining % |
| `is_at_liquidation_risk` | `(price, max_pct=95) -> bool` | True if near liquidation |

---

## financepype.markets.funding

### FundingPaymentType

`NEXT`, `LAST`

### FundingInfo

```
class FundingInfo(BaseModel)
```

| Field | Type |
|-------|------|
| `trading_pair` | `TradingPair` |
| `index_price` | `Decimal` |
| `mark_price` | `Decimal` |
| `next_funding_utc_timestamp` | `int \| None` |
| `next_funding_rate` | `Decimal` |
| `last_funding_utc_timestamp` | `int \| None` |
| `last_funding_rate` | `Decimal` |
| `payment_type` | `FundingPaymentType` |
| `live_payment_frequency` | `int \| None` |
| `utc_timestamp` | `int \| None` |

**Properties**

- `payment_seconds_interval -> int | None`
- `has_live_payments -> bool`

**Methods**

- `update(info_update: FundingInfoUpdate) -> None`
- `get_next_payment_rates(payment_seconds_format?, closing_time?, current_time_function?) -> dict[int, Decimal] | None`

### FundingPayment

| Field | Type | Description |
|-------|------|-------------|
| `trading_pair` | `TradingPair` | |
| `amount` | `Decimal` | Absolute amount |
| `is_received` | `bool` | Direction |
| `timestamp` | `int` | Unix timestamp |
| `settlement_token` | `str` | Token used for settlement |
| `funding_id` | `str` | Unique payment ID |

**Properties**: `signed_amount -> Decimal` (positive if received)

---

## financepype.markets.rates

See `FundingInfo` / `FundingPayment` for the same pattern applied to borrow (`BorrowInfo`, `BorrowPayment`) and staking (`StakingInfo`, `StakingPayment`).

### RatePaymentType

`NEXT`, `LAST`

### BorrowInfo / StakingInfo

Same structure as `FundingInfo` but for borrow/staking rates. `BorrowInfo` adds `utilization_rate`. `StakingInfo` adds `reward_asset` and `total_staked`.

---

## financepype.markets.lending

### BorrowPosition

| Field | Type | Constraint |
|-------|------|------------|
| `borrowed_asset` | `Asset` | |
| `collateral_asset` | `Asset` | |
| `borrowed_amount` | `Decimal` | `> 0` |
| `collateral_amount` | `Decimal` | `>= 0` |
| `interest_rate` | `Decimal` | `>= 0` |
| `entry_timestamp` | `int` | |
| `accrued_interest` | `Decimal` | `>= 0`, default 0 |
| `liquidation_threshold` | `Decimal` | `(0, 100]` |

**Properties**: `total_debt`, `collateral_ratio`

**Methods**: `is_at_liquidation_risk(...)`, `calculate_interest_for_period(...)`, `update_accrued_interest(...)`

### StakingPosition

| Field | Description |
|-------|-------------|
| `staked_asset` | Asset being staked |
| `reward_asset` | Asset for reward payments |
| `staked_amount` | Amount staked |
| `reward_rate` | APY as percentage |
| `entry_timestamp` | When staking started |

**Properties**: `is_locked`, `time_until_unlock`

**Methods**: `calculate_rewards_for_period(...)`, `update_accrued_rewards(...)`, `calculate_compound_rewards(...)`
