import pytest

from financepype.operators.exchanges.exchange import ExchangeConfiguration
from financepype.operators.operator import Operator
from financepype.platforms.platform import Platform


class ConcreteOperator(Operator):
    """A concrete implementation of Operator for testing."""

    pass


@pytest.fixture
def test_platform() -> Platform:
    """Create a test platform."""
    return Platform(identifier="test_platform")


def test_operator_initialization(platform: Platform) -> None:
    """Test that a concrete operator is properly initialized."""
    operator = ConcreteOperator(ExchangeConfiguration(platform=platform))
    assert isinstance(operator, Operator)
