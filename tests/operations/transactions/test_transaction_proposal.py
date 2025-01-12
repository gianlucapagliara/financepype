from typing import Any
from unittest.mock import Mock

import pytest

from financepype.operations.transactions.proposal import TransactionProposal
from financepype.operations.transactions.transaction import BlockchainTransaction
from financepype.owners.owner_id import OwnerIdentifier
from financepype.platforms.platform import Platform


class ConcreteTransactionProposal(TransactionProposal):
    """Concrete implementation of TransactionProposal for testing."""

    def __init__(
        self,
        owner_identifier: OwnerIdentifier,
        mock_function=None,
        mock_kwargs=None,
        purpose: str = "test_purpose",
    ):
        super().__init__(purpose=purpose, owner_identifier=owner_identifier)
        self._mock_function = mock_function or Mock(
            return_value=Mock(spec=BlockchainTransaction)
        )
        self._mock_kwargs = mock_kwargs or {"test_arg": "test_value"}

    @property
    def execute_function(self):
        return self._mock_function

    @property
    def execute_kwargs(self):
        return self._mock_kwargs

    def _prepare_update(self, event: Any) -> None:
        """Mock implementation of prepare_update."""
        pass

    def _update_costs(self, event: Any) -> None:
        """Mock implementation of update_costs."""
        pass

    def _update_state(self, event: Any) -> None:
        """Mock implementation of update_state."""
        pass

    def _update_result(self, event: Any) -> None:
        """Mock implementation of update_result."""
        pass

    def _validate_update(self, event: Any) -> None:
        """Mock implementation of validate_update."""
        pass

    def _update_fees(self, event: Any) -> None:
        """Mock implementation of update_fees."""
        pass

    def _update_returns(self, event: Any) -> None:
        """Mock implementation of update_returns."""
        pass

    def _update_gas(self, event: Any) -> None:
        """Mock implementation of update_gas."""
        pass

    def _update_totals(self, event: Any) -> None:
        """Mock implementation of update_totals."""
        pass


class MockPlatform(Platform):
    """Mock platform for testing."""

    def __init__(self):
        super().__init__(identifier="test_platform", name="test_platform")


@pytest.fixture
def platform():
    return MockPlatform()


@pytest.fixture
def owner_identifier(platform):
    return OwnerIdentifier(name="test_owner", platform=platform)


@pytest.fixture
def mock_transaction():
    return Mock(spec=BlockchainTransaction)


@pytest.fixture
def mock_execute_function(mock_transaction):
    return Mock(return_value=mock_transaction)


def test_transaction_proposal_initialization(owner_identifier):
    """Test that TransactionProposal initializes correctly."""
    proposal = ConcreteTransactionProposal(owner_identifier)
    assert proposal.owner_identifier == owner_identifier
    assert proposal.executed_operation is None
    assert not proposal.executed


def test_can_be_executed_property(owner_identifier):
    """Test that can_be_executed always returns True for TransactionProposal."""
    proposal = ConcreteTransactionProposal(owner_identifier)
    assert proposal.can_be_executed is True


def test_execute_function_property(owner_identifier, mock_execute_function):
    """Test that execute_function returns the correct callable."""
    proposal = ConcreteTransactionProposal(
        owner_identifier, mock_function=mock_execute_function
    )
    assert proposal.execute_function == mock_execute_function


def test_execute_kwargs_property(owner_identifier):
    """Test that execute_kwargs returns the correct dictionary."""
    test_kwargs = {"arg1": "value1", "arg2": "value2"}
    proposal = ConcreteTransactionProposal(owner_identifier, mock_kwargs=test_kwargs)
    assert proposal.execute_kwargs == test_kwargs


def test_successful_execution(
    owner_identifier, mock_transaction, mock_execute_function
):
    """Test successful execution of a transaction proposal."""
    proposal = ConcreteTransactionProposal(
        owner_identifier, mock_function=mock_execute_function
    )

    result = proposal.execute()

    assert result == mock_transaction
    assert proposal.executed_operation == mock_transaction
    assert proposal.executed
    mock_execute_function.assert_called_once_with(test_arg="test_value")


def test_execute_already_executed(owner_identifier):
    """Test that executing an already executed proposal raises ValueError."""
    proposal = ConcreteTransactionProposal(owner_identifier)
    proposal.execute()

    with pytest.raises(ValueError, match="Proposal already executed."):
        proposal.execute()


def test_execute_with_custom_kwargs(owner_identifier, mock_execute_function):
    """Test execution with custom keyword arguments."""
    custom_kwargs = {"custom_arg": "custom_value"}
    proposal = ConcreteTransactionProposal(
        owner_identifier, mock_function=mock_execute_function, mock_kwargs=custom_kwargs
    )

    proposal.execute()

    mock_execute_function.assert_called_once_with(custom_arg="custom_value")
