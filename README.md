# Finance Pypeline

A Python framework for managing and executing trading operations across multiple platforms with a focus on reliability and consistency.

## Overview

financepype is a modular trading framework designed to:
- Handle multi-platform trading operations
- Manage trading pairs and balances
- Track operations and their states
- Enforce trading rules and validations
- Support both spot and perpetual trading

It is inspired by some of the concepts used in [hummingbot](https://github.com/hummingbot/hummingbot), but with a focus on simplicity and flexibility.

## Features

- **Multi-Platform Support**: Seamlessly integrate with both centralized and decentralized exchanges
- **Advanced Order Management**:
  - Support for various order types (Market, Limit)
  - Order modifiers (Post-Only, Reduce-Only, IOC, FOK)
  - Position management for derivatives trading
- **Asset Management**:
  - Spot trading support
  - Perpetual futures trading
  - Options trading support
  - Blockchain asset integration
- **Balance Tracking**:
  - Real-time balance updates
  - Multi-currency support
  - PnL tracking
- **Trading Rules Engine**:
  - Customizable trading rules
  - Risk management constraints
  - Position sizing rules
- **Operation Tracking**:
  - Order state management
  - Transaction tracking
  - Fee calculation and tracking

## Installation

The package requires Python 3.13 or later. You can install it using Poetry:

```bash
poetry add financepype
```

Or with pip:

```bash
pip install financepype
```

## Quick Start

Here's a simple example of how to use financepype:

```python
from financepype.assets.factory import AssetFactory
from financepype.platforms.platform import Platform
from financepype.markets.trading_pair import TradingPair

# Initialize platform
platform = Platform(identifier="binance")

# Get assets
btc = AssetFactory.get_asset(platform, "BTC")
usdt = AssetFactory.get_asset(platform, "USDT")

# Create trading pair
trading_pair = TradingPair(name="BTC-USDT")
```

## Development

### Setup

1. Clone the repository:
```bash
git clone https://github.com/gianlucapagliara/financepype.git
cd financepype
```

2. Install dependencies with Poetry:
```bash
poetry install
```

3. Set up pre-commit hooks:
```bash
poetry run pre-commit install
```

### Testing

Run the test suite:

```bash
poetry run pytest
```

### Code Quality

The project uses several tools to maintain code quality:
- Black for code formatting
- isort for import sorting
- mypy for static type checking
- ruff for linting
- pre-commit hooks for automated checks

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
