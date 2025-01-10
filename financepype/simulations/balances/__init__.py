"""Balance simulation and tracking package.

This package provides tools for simulating and tracking balances across different
types of financial markets. It includes simulation engines for various market
types and tracking mechanisms for monitoring balance changes.

The package is organized into two main components:

1. Engines (engines/):
   Simulation engines for different market types:
   - Spot markets (spot.py)
   - Perpetual futures (perpetual.py)
   - Options (option.py)
   - Multi-market coordination (multiengine.py)
   - Base engine interface (engine.py)
   - Common models (models.py)
   - Dashboard visualization (dashboard.py)

2. Tracking (tracking/):
   Balance tracking and monitoring tools:
   - Balance tracker (tracker.py)
   - Position locking (lock.py)

Example:
    >>> from financepype.simulations.balances.engines import SpotEngine
    >>> from financepype.simulations.balances.tracking import BalanceTracker
    >>>
    >>> # Initialize simulation components
    >>> engine = SpotEngine(initial_balance=1000.0)
    >>> tracker = BalanceTracker(engine)
    >>>
    >>> # Run simulation
    >>> engine.simulate_market_order(...)
    >>>
    >>> # Check results
    >>> print(tracker.get_pnl())

Note:
    Each simulation engine implements safeguards and validation to ensure
    realistic market behavior, but should still be used with caution in
    production environments.
"""
