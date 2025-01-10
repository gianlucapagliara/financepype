"""Trading rules and constraints management for financial instruments.

This package provides functionality for defining and managing trading rules
and constraints for various financial instruments across different exchanges
and platforms. It includes:

- Base trading rules for spot markets
- Extended rules for derivative instruments
- Trading rules tracking and validation
- Symbol mapping between exchange-specific and standardized formats

The rules system ensures that all trading operations comply with
exchange-specific limitations and requirements, such as:
- Minimum and maximum order sizes
- Price tick sizes and increments
- Supported order types and modifiers
- Trading schedules and expiration times (for derivatives)
- Platform-specific trading constraints

The package is designed to be extensible, allowing easy addition of new
exchange-specific rules and validation logic. The core components are:

1. TradingRule: Base class for spot market trading rules
   - Order size and price increment validation
   - Notional value limits
   - Order type support

2. DerivativeTradingRule: Extended rules for derivatives
   - Expiration time management
   - Linear/inverse contract support
   - Strike price handling for options

3. TradingRulesTracker: Thread-safe rules management
   - Symbol mapping and validation
   - Asynchronous rule updates
   - Exchange integration support

Example:
    >>> from financepype.rules import TradingRule, TradingRulesTracker
    >>> # Create a trading rule for a spot market
    >>> rule = TradingRule(
    ...     trading_pair=TradingPair(name="BTC-USDT"),
    ...     min_order_size=Decimal("0.001"),
    ...     min_price_increment=Decimal("0.01")
    ... )
    >>> # Track and validate trading rules
    >>> tracker = MyExchangeRulesTracker()
    >>> await tracker.update_trading_rules()
"""
