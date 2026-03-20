# Contributing

Contributions to FinancePype are welcome. This guide explains how to set up a development environment, follow the project conventions, and submit changes.

## Development Setup

### Prerequisites

- Python 3.13 or later
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Clone and Install

```bash
git clone https://github.com/gianlucapagliara/financepype.git
cd financepype

# Install all dependencies including dev and docs groups
uv sync --group dev --group docs

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
pytest
```

With coverage report:

```bash
pytest --cov=financepype --cov-report=html
open htmlcov/index.html
```

Run a specific test file:

```bash
pytest tests/test_assets.py -v
```

The test suite uses `pytest-asyncio` in auto mode — all async test functions are detected automatically.

### Code Quality Tools

The project enforces quality via pre-commit hooks that run automatically on each commit.

**Linting** (ruff):

```bash
ruff check financepype/
ruff check financepype/ --fix  # auto-fix where possible
```

**Type checking** (mypy):

```bash
mypy financepype/
```

**Format checking** (ruff format):

```bash
ruff format --check financepype/
ruff format financepype/
```

### Documentation

```bash
# Live preview
mkdocs serve

# Build static site
mkdocs build
```

## Project Structure

```
financepype/
├── financepype/              # Library source
│   ├── assets/               # Asset types and factory
│   ├── constants.py          # Shared constants
│   ├── data_loaders/         # CSV/Parquet market data loaders
│   ├── markets/              # Market data models
│   ├── operations/           # Orders and transactions
│   │   ├── orders/
│   │   └── transactions/
│   ├── operators/            # Exchange/blockchain connectors
│   │   ├── blockchains/
│   │   ├── dapps/
│   │   └── exchanges/
│   ├── owners/               # Account owners
│   ├── platforms/            # Platform definitions
│   ├── rules/                # Trading rules
│   ├── secrets/              # Credential management
│   └── simulations/          # Balance simulation
│       └── balances/
│           ├── engines/
│           └── tracking/
├── tests/                    # Test suite
├── docs/                     # Documentation source
├── mkdocs.yml                # Documentation config
└── pyproject.toml            # Project config
```

## Code Style

### Formatting

- **Line length**: 88 characters (configured in `pyproject.toml`)
- **Formatter**: `ruff format`
- **Import sorting**: `ruff` with isort rules

### Type Hints

All public functions and methods must have complete type annotations. The project uses strict mypy configuration:

```toml
[tool.mypy]
strict = true
disallow_untyped_defs = true
check_untyped_defs = true
warn_return_any = true
```

### Pydantic Models

- Use `model_config = ConfigDict(frozen=True)` for immutable models.
- Use `Field(description="...")` on all public model fields.
- Prefer `field_validator` over `__init__` overrides.
- Use `model_validator(mode="after")` for cross-field validation.

### Docstrings

All public classes and methods should have Google-style docstrings:

```python
def calculate_fee(amount: Decimal, rate: Decimal) -> Decimal:
    """Calculate the fee for an operation.

    Args:
        amount: The operation amount in quote currency.
        rate: The fee rate as a decimal percentage (e.g., 0.1 for 0.1%).

    Returns:
        The calculated fee amount.

    Raises:
        ValueError: If amount or rate is negative.
    """
    ...
```

## Adding a New Exchange Connector

1. Create a module under `financepype/operators/exchanges/` (e.g., `binance.py`).
2. Subclass `ExchangeOperator` or `OrderbookExchange`.
3. Implement all abstract methods.
4. Subclass `TradingRulesTracker` and implement `update_trading_rules`.
5. Write tests under `tests/operators/`.

## Adding a New Balance Engine

1. Create a module under `financepype/simulations/balances/engines/` (e.g., `my_engine.py`).
2. Subclass `BalanceEngine`.
3. Implement all five abstract class methods.
4. Add tests under `tests/simulations/`.
5. Register it in `MultiEngine` if it should be used automatically.

## Submitting a Pull Request

1. Fork the repository and create a branch from `main`.
2. Make your changes with appropriate tests.
3. Ensure all checks pass: `pytest`, `mypy`, `ruff`.
4. Update documentation if public APIs changed.
5. Open a pull request with a clear description of the change.

### Commit Messages

Follow conventional commits style:

```
feat: add support for options balance engine
fix: correct collateral token default for inverse derivatives
docs: add TradingRulesTracker API reference
refactor: extract nonce creation to NonceCreator class
test: add order lifecycle integration tests
```

## Reporting Issues

File issues at [github.com/gianlucapagliara/financepype/issues](https://github.com/gianlucapagliara/financepype/issues).

Include:
- Python version (`python --version`)
- financepype version (`pip show financepype`)
- Minimal reproducible example
- Expected vs. actual behaviour
- Full stack trace if applicable

## License

By contributing, you agree that your changes will be licensed under the [MIT License](https://github.com/gianlucapagliara/financepype/blob/main/LICENSE).
