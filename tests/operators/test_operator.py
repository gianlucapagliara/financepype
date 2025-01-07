from unittest.mock import patch

import pytest
from chronopype.processors.network import NetworkProcessor

from financepype.operators.operator import Operator
from financepype.platforms.platform import Platform


class ConcreteOperator(Operator):
    """A concrete implementation of Operator for testing."""

    def check_network(self) -> bool:
        """Test implementation that always returns True."""
        return True


@pytest.fixture
def test_platform() -> Platform:
    """Create a test platform."""
    return Platform(identifier="test_platform")


def test_operator_inheritance() -> None:
    """Test that Operator inherits from NetworkProcessor."""
    assert issubclass(Operator, NetworkProcessor)


def test_concrete_operator_initialization(test_platform: Platform) -> None:
    """Test that a concrete operator is properly initialized."""
    with patch.object(NetworkProcessor, "__init__", return_value=None) as mock_init:
        operator = ConcreteOperator(platform=test_platform)
        assert isinstance(operator, NetworkProcessor)
        mock_init.assert_called_once_with()


def test_concrete_operator_check_network(test_platform: Platform) -> None:
    """Test that check_network can be implemented."""
    operator = ConcreteOperator(platform=test_platform)
    assert operator.check_network() is True
