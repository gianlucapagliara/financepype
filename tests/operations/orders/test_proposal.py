import pytest

from financepype.operations.orders.proposal import OrderProposal


class ConcreteOrderProposal(OrderProposal):
    """A concrete implementation of OrderProposal for testing."""

    def _prepare_update(self) -> None:
        """Test implementation that does nothing."""
        pass

    def _update_costs(self) -> None:
        """Test implementation that does nothing."""
        pass

    def _update_fees(self) -> None:
        """Test implementation that does nothing."""
        pass

    def _update_returns(self) -> None:
        """Test implementation that does nothing."""
        pass

    def _update_totals(self) -> None:
        """Test implementation that does nothing."""
        pass


@pytest.fixture
def order_proposal() -> OrderProposal:
    return ConcreteOrderProposal(purpose="test", client_id_prefix="TEST_")


def test_order_proposal_initialization(order_proposal: OrderProposal) -> None:
    """Test that an order proposal is properly initialized."""
    assert order_proposal.purpose == "test"
    assert order_proposal.client_id_prefix == "TEST_"
    assert order_proposal.potential_costs is None
    assert order_proposal.potential_returns is None
    assert order_proposal.potential_fees is None
    assert order_proposal.potential_total_costs is None
    assert order_proposal.potential_total_returns is None
    assert order_proposal.executed_operation is None


def test_order_proposal_initialized_property(order_proposal: OrderProposal) -> None:
    """Test the initialized property."""
    assert not order_proposal.initialized
    order_proposal.update_proposal()
    assert order_proposal.initialized


def test_order_proposal_executed_property(order_proposal: OrderProposal) -> None:
    """Test the executed property."""
    assert not order_proposal.executed
    order_proposal.executed_operation = None
    assert not order_proposal.executed
