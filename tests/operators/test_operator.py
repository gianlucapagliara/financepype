from unittest.mock import patch

from chronopype.processors.network import NetworkProcessor

from financepype.operators.operator import Operator


class ConcreteOperator(Operator):
    """A concrete implementation of Operator for testing."""

    def check_network(self) -> bool:
        """Test implementation that always returns True."""
        return True


def test_operator_inheritance() -> None:
    """Test that Operator inherits from NetworkProcessor."""
    assert issubclass(Operator, NetworkProcessor)


def test_concrete_operator_initialization() -> None:
    """Test that a concrete operator is properly initialized."""
    with patch.object(NetworkProcessor, "__init__", return_value=None) as mock_init:
        operator = ConcreteOperator()
        assert isinstance(operator, NetworkProcessor)
        mock_init.assert_called_once_with()


def test_concrete_operator_check_network() -> None:
    """Test that check_network can be implemented."""
    operator = ConcreteOperator()
    assert operator.check_network() is True
