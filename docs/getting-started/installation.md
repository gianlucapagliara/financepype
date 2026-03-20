# Installation

## Requirements

- Python **3.13** or later
- An operating system supported by Python (Linux, macOS, Windows)

## Installing with pip

```bash
pip install financepype
```

## Installing with uv

[uv](https://github.com/astral-sh/uv) is the recommended package manager for fast installs and reproducible environments.

```bash
uv add financepype
```

Or as a development dependency:

```bash
uv add --dev financepype
```

## Installing with Poetry

```bash
poetry add financepype
```

## Installing from Source

Clone the repository and install in editable mode:

```bash
git clone https://github.com/gianlucapagliara/financepype.git
cd financepype
pip install -e .
```

With uv and the development dependency group:

```bash
uv sync --group dev
```

## Optional Dependencies

### Parquet File Support

Loading market data from Parquet files requires `pandas`, which is included in the default dependencies:

```bash
pip install financepype[pandas]
```

If you installed the base package without pandas, add it manually:

```bash
pip install pandas>=2.2
```

### AWS Secrets Manager

AWS integration requires `boto3`, which is included in the default install. No additional steps are needed unless you need a specific AWS SDK version.

## Verifying the Installation

```python
import financepype
from financepype.platforms.platform import Platform
from financepype.markets.trading_pair import TradingPair

platform = Platform(identifier="test")
pair = TradingPair(name="BTC-USDT")
print(f"Platform: {platform}")
print(f"Trading pair: {pair}, base={pair.base}, quote={pair.quote}")
```

## Development Setup

To set up a full development environment with linting, type checking, and testing tools:

```bash
git clone https://github.com/gianlucapagliara/financepype.git
cd financepype

# Install all dependencies including dev group
uv sync --group dev --group docs

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=financepype --cov-report=html
```

### Linting and Type Checking

```bash
ruff check financepype/
mypy financepype/
```

### Building Documentation

```bash
mkdocs serve        # live preview at http://127.0.0.1:8000
mkdocs build        # build static site into site/
```
