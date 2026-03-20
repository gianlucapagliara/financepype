# API Reference — Data Loaders

## financepype.data_loaders.data_models

### DataType

```
class DataType(Enum)
```

`FUNDING`, `CANDLE`, `BORROW`, `STAKING`

### FundingData

```
class FundingData(BaseModel)
```

| Field | Type | Description |
|-------|------|-------------|
| `exchange` | `str` | Exchange name |
| `market` | `str` | Trading pair |
| `timestamp` | `int` | Row timestamp (ms) |
| `funding_timestamp` | `int` | Actual payment timestamp (ms) |
| `next_funding_rate` | `Decimal` | Funding rate |
| `index_price` | `Decimal \| None` | Index price |
| `mark_price` | `Decimal \| None` | Mark price |

**Methods**

- `to_funding_info() -> FundingInfo`
- `to_platform() -> Platform`

### CandleData

```
class CandleData(BaseModel)
```

| Field | Type | Description |
|-------|------|-------------|
| `exchange` | `str` | Exchange name |
| `market` | `str` | Trading pair |
| `timestamp` | `int` | Row timestamp (ms) |
| `start_time` | `int` | Candle open time (ms) |
| `end_time` | `int` | Candle close time (ms) |
| `open` | `Decimal` | Open price |
| `high` | `Decimal` | High price |
| `low` | `Decimal` | Low price |
| `close` | `Decimal` | Close price |
| `volume` | `Decimal \| None` | Volume |

**Methods**

- `to_candle() -> Candle`

### BorrowData

```
class BorrowData(BaseModel)
```

| Field | Type | Description |
|-------|------|-------------|
| `exchange` | `str` | Exchange name |
| `market` | `str` | Asset symbol |
| `timestamp` | `int` | Row timestamp (ms) |
| `current_rate` | `Decimal` | Current APR |
| `next_rate` | `Decimal \| None` | Next rate |
| `utilization_rate` | `Decimal \| None` | Pool utilization % |

**Methods**

- `to_borrow_info() -> BorrowInfo`

### StakingData

```
class StakingData(BaseModel)
```

| Field | Type | Description |
|-------|------|-------------|
| `exchange` | `str` | Exchange name |
| `market` | `str` | Asset symbol |
| `timestamp` | `int` | Row timestamp (ms) |
| `reward_rate` | `Decimal` | Current APY |
| `total_staked` | `Decimal \| None` | Pool total |

**Methods**

- `to_staking_info() -> StakingInfo`

---

## financepype.data_loaders.csv_loader

### CSVDataLoader

```
class CSVDataLoader
```

Loads market data from CSV and Parquet files.

**Static Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `_detect_data_type` | `(headers: list[str]) -> DataType` | Auto-detect from column names |
| `_load_csv_data` | `(file_path) -> list[dict]` | Read CSV rows |
| `_load_parquet_data` | `(file_path) -> list[dict]` | Read Parquet rows (requires pandas) |

**Methods**

| Method | Signature | Returns |
|--------|-----------|---------|
| `load_data` | `(file_path, data_type=None, **kwargs) -> list[BaseModel]` | Generic loader |
| `load_funding_data` | `(file_path, **kwargs) -> list[FundingData]` | |
| `load_candle_data` | `(file_path, **kwargs) -> list[CandleData]` | |
| `load_borrow_data` | `(file_path, **kwargs) -> list[BorrowData]` | |
| `load_staking_data` | `(file_path, **kwargs) -> list[StakingData]` | |

**`load_data` file format detection**

Supported extensions: `.csv`, `.parquet`, `.pq`

**`_detect_data_type` column detection**

| Type | Indicator columns |
|------|------------------|
| `FUNDING` | `funding_rate`, `next_funding_rate`, `funding_timestamp`, `index_price`, `mark_price` |
| `CANDLE` | ≥4 of `open`, `close`, `high`, `low`, `start_time`, `end_time` |
| `BORROW` | `current_rate`, `utilization_rate`, `borrow` |
| `STAKING` | `reward_rate`, `total_staked`, `staking` |

---

## financepype.data_loaders.market_data_loader

### MarketDataLoader

```
class MarketDataLoader
```

Extends `CSVDataLoader` capabilities with simulation integration.

**Constructor**

```python
MarketDataLoader()
```

Creates a `CSVDataLoader` internally.

**Load Methods** (delegate to `CSVDataLoader`)

- `load_funding_data(file_path, **kwargs) -> list[FundingData]`
- `load_candle_data(file_path, **kwargs) -> list[CandleData]`
- `load_borrow_data(file_path, **kwargs) -> list[BorrowData]`
- `load_staking_data(file_path, **kwargs) -> list[StakingData]`

**Conversion Methods**

| Method | Signature | Returns |
|--------|-----------|---------|
| `convert_funding_data_to_info` | `(data: list[FundingData]) -> list[FundingInfo]` | |
| `convert_candle_data_to_candles` | `(data: list[CandleData]) -> list[Candle]` | |
| `convert_borrow_data_to_info` | `(data: list[BorrowData]) -> list[BorrowInfo]` | |
| `convert_staking_data_to_info` | `(data: list[StakingData]) -> list[StakingInfo]` | |

**Query Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_funding_rate_at_timestamp` | `(data, timestamp: int) -> FundingData \| None` | Closest by timestamp |
| `get_candle_at_timestamp` | `(data, timestamp: int) -> CandleData \| None` | Candle containing timestamp |

**Filter Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `filter_data_by_timerange` | `(data, start_time, end_time) -> list` | Keep rows within range |
| `filter_funding_payments` | `(data: list[FundingData]) -> list[FundingData]` | Keep actual payment rows |
| `get_unique_markets` | `(data) -> set[str]` | Unique market symbols |
| `get_unique_exchanges` | `(data) -> set[str]` | Unique exchange names |

**Simulation Methods**

| Method | Signature | Description |
|--------|-----------|-------------|
| `create_funding_order_from_data` | `(funding_data, position_size, position_side, settlement_asset, fee_amount=0) -> FundingOrderDetails` | Build simulation input |
| `simulate_funding_payments` | `(funding_data, simulation_engine, position_size, position_side, settlement_asset, fee_amount=0) -> list` | Simulate over all data points |
| `load_and_simulate_funding` | `(file_path, simulation_engine, position_size, position_side, settlement_asset, fee_amount=0, start_time=None, end_time=None) -> list` | Load + filter + simulate |
