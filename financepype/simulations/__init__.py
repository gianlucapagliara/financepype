"""Financial market simulation package.

This package provides a comprehensive framework for simulating various financial
market scenarios and trading strategies. It includes tools for simulating different
types of trading environments, balance tracking, and performance analysis.

Key Components:
1. Balance Simulation (balances/):
   - Engine-based simulation of different market types
   - Spot market simulation
   - Perpetual futures simulation
   - Options market simulation
   - Multi-engine coordination for complex strategies

2. Balance Tracking (balances/tracking/):
   - Real-time balance tracking
   - Position locking mechanisms
   - Performance monitoring

The simulation framework is designed to be:
- Modular: Each component can be used independently
- Extensible: Easy to add new simulation engines
- Accurate: Closely mimics real market behavior
- Safe: Includes safeguards against common simulation pitfalls

Example:
    >>> from financepype.simulations.balances.engines import SpotEngine
    >>> from financepype.simulations.balances.tracking import BalanceTracker
    >>>
    >>> # Create a spot market simulation engine
    >>> engine = SpotEngine(...)
    >>>
    >>> # Set up balance tracking
    >>> tracker = BalanceTracker(engine)
    >>>
    >>> # Run simulation
    >>> engine.simulate_trade(...)
    >>>
    >>> # Monitor results
    >>> tracker.get_current_balance()

Note:
    This package is intended for simulation purposes only and should not be
    used for actual trading without proper risk management and validation.
"""
