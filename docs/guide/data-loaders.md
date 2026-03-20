# Data Loaders

The `data_loaders` module provides utilities for loading historical market data from CSV and Parquet files, and integrating that data with the simulation framework.

## CSVDataLoader

`CSVDataLoader` reads market data files and converts them to typed Pydantic models.

```python
from financepype.data_loaders.csv_loader import CSVDataLoader
from financepype.data_loaders.data_models import DataType

loader = CSVDataLoader()
```

### Loading Specific Data Types

```python
# Funding rate data
funding_data = loader.load_funding_data("funding_rates.csv")

# OHLCV candle data
candle_data = loader.load_candle_data("btc_1h_candles.csv")

# Borrow rate data
borrow_data = loader.load_borrow_data("borrow_rates.csv")

# Staking reward data
staking_data = loader.load_staking_data("staking_rewards.csv")
```

### Automatic Type Detection

`load_data()` can detect the data type from column headers:

```python
data = loader.load_data("unknown_data.csv")  # auto-detects type
data = loader.load_data("file.parquet")       # Parquet also supported
data = loader.load_data("file.csv", data_type=DataType.FUNDING)  # explicit
```

Detection logic:
- **FUNDING**: headers contain `funding_rate`, `next_funding_rate`, `index_price`, or `mark_price`
- **CANDLE**: ≥4 of `open`, `close`, `high`, `low`, `start_time`, `end_time`
- **BORROW**: headers contain `current_rate` or `utilization_rate`
- **STAKING**: headers contain `reward_rate` or `total_staked`

### Parquet Support

Parquet files (`.parquet` or `.pq`) require `pandas`:

```python
data = loader.load_data("btc_funding.parquet")
```

## Data Models

### FundingData

```python
from financepype.data_loaders.data_models import FundingData

row = FundingData(
    exchange="binance",
    market="BTC-USDT-PERPETUAL",
    timestamp=1700000000000,        # milliseconds
    funding_timestamp=1700000000000,
    next_funding_rate="0.01",       # as string or Decimal
    index_price="50000",
    mark_price="50050",
)

# Convert to FundingInfo for simulation
funding_info = row.to_funding_info()
```

### CandleData

```python
from financepype.data_loaders.data_models import CandleData

row = CandleData(
    exchange="binance",
    market="BTC-USDT",
    timestamp=1700000000000,
    start_time=1700000000000,
    end_time=1700003600000,
    open="50000",
    high="51000",
    low="49800",
    close="50500",
    volume="123.45",
)

candle = row.to_candle()  # returns financepype.markets.candle.Candle
```

### BorrowData

```python
from financepype.data_loaders.data_models import BorrowData

row = BorrowData(
    exchange="binance",
    market="USDT",
    timestamp=1700000000000,
    current_rate="5.0",   # APR percentage
    next_rate="5.1",
    utilization_rate="80.0",
)

borrow_info = row.to_borrow_info()
```

### StakingData

```python
from financepype.data_loaders.data_models import StakingData

row = StakingData(
    exchange="binance",
    market="BTC",
    timestamp=1700000000000,
    reward_rate="3.0",    # APY percentage
    total_staked="50000",
)

staking_info = row.to_staking_info()
```

## MarketDataLoader

`MarketDataLoader` extends `CSVDataLoader` with simulation integration utilities.

```python
from financepype.data_loaders.market_data_loader import MarketDataLoader

loader = MarketDataLoader()
```

### Loading and Converting

```python
# Load and convert to domain objects in one step
funding_infos = loader.convert_funding_data_to_info(
    loader.load_funding_data("funding.csv")
)
candles = loader.convert_candle_data_to_candles(
    loader.load_candle_data("candles.csv")
)
```

### Querying Data

```python
# Find the closest funding data point to a timestamp (milliseconds)
closest = loader.get_funding_rate_at_timestamp(funding_data, timestamp=1700000000000)

# Find the candle that contains a timestamp
candle = loader.get_candle_at_timestamp(candle_data, timestamp=1700001800000)
```

### Filtering

```python
# Filter by timestamp range (milliseconds)
filtered = loader.filter_data_by_timerange(
    funding_data,
    start_time=1700000000000,
    end_time=1700086400000,
)

# Keep only actual funding payment timestamps (not rate updates)
payments = loader.filter_funding_payments(funding_data)

# Get unique markets and exchanges in a dataset
markets = loader.get_unique_markets(funding_data)    # set[str]
exchanges = loader.get_unique_exchanges(funding_data) # set[str]
```

### Simulation Integration

`MarketDataLoader` can directly run funding payment simulations from historical data:

```python
from decimal import Decimal
from financepype.assets.factory import AssetFactory
from financepype.platforms.platform import Platform
from financepype.simulations.simulation import BalanceSimulationEngine
from financepype.simulations.balances.tracking.tracker import BalanceTracker

platform = Platform(identifier="sim")
usdt = AssetFactory.get_asset(platform, "USDT")

tracker = BalanceTracker()
engine = BalanceSimulationEngine(tracker)

# Run simulation over historical funding data
results = loader.simulate_funding_payments(
    funding_data=funding_data,
    simulation_engine=engine,
    position_size=Decimal("1.0"),       # 1 BTC position
    position_side="LONG",
    settlement_asset=usdt,
    fee_amount=Decimal("0"),
)
```

### Combined Load + Simulate

```python
results = loader.load_and_simulate_funding(
    file_path="btc_funding_2025.csv",
    simulation_engine=engine,
    position_size=Decimal("1.0"),
    position_side="LONG",
    settlement_asset=usdt,
    start_time=1700000000000,  # optional filter
    end_time=1702678400000,
)
```

## Expected CSV Column Names

### Funding CSV

| Column | Description |
|--------|-------------|
| `exchange` | Exchange name |
| `market` | Trading pair (e.g., BTC-USDT-PERPETUAL) |
| `timestamp` | Row timestamp (ms) |
| `funding_timestamp` | Actual funding payment timestamp (ms) |
| `next_funding_rate` | Funding rate as decimal percentage |
| `index_price` | Index price |
| `mark_price` | Mark price |

### Candle CSV

| Column | Description |
|--------|-------------|
| `exchange` | Exchange name |
| `market` | Trading pair |
| `timestamp` | Row timestamp (ms) |
| `start_time` | Candle open time (ms) |
| `end_time` | Candle close time (ms) |
| `open` | Open price |
| `high` | High price |
| `low` | Low price |
| `close` | Close price |
| `volume` | Volume (optional) |

### Borrow CSV

| Column | Description |
|--------|-------------|
| `exchange` | Exchange name |
| `market` | Asset symbol |
| `timestamp` | Row timestamp (ms) |
| `current_rate` | Current borrow rate (% APR) |
| `next_rate` | Next rate (optional) |
| `utilization_rate` | Pool utilization % (optional) |

### Staking CSV

| Column | Description |
|--------|-------------|
| `exchange` | Exchange name |
| `market` | Asset symbol |
| `timestamp` | Row timestamp (ms) |
| `reward_rate` | Reward rate (% APY) |
| `total_staked` | Total pool staked amount (optional) |
