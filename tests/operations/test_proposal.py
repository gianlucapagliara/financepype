import time
from decimal import Decimal
from typing import Any

import pytest

from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.spot import SpotAsset
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee
from financepype.operations.operation import Operation
from financepype.operations.proposal import OperationProposal
from financepype.owners.owner import NamedOwnerIdentifier
from financepype.platforms.platform import Platform


class MockOperation(Operation):
    """A simple operation implementation for testing."""

    def __init__(self, purpose: str):
        current_time = time.time()
        super().__init__(
            client_operation_id="test_op",
            owner_identifier=NamedOwnerIdentifier(
                name="test_owner", platform=Platform(identifier="test")
            ),
            creation_timestamp=current_time,
            current_state=None,
            other_data={"purpose": purpose},
        )

    @property
    def purpose(self) -> str:
        """Get the purpose of this test operation."""
        purpose = self.other_data.get("purpose")
        if not isinstance(purpose, str):
            raise ValueError("Purpose must be a string")
        return purpose

    def process_operation_update(self, update: Any) -> bool:
        """Test implementation that does nothing."""
        return True


class MockProposal(OperationProposal):
    """A concrete implementation of OperationProposal for testing."""

    def _prepare_update(self) -> None:
        """Test implementation that does nothing."""
        pass

    def _update_costs(self) -> None:
        """Test implementation that adds a simple cost."""
        if self.potential_costs is None:
            self.potential_costs = {}
        platform = Platform(identifier="test")
        asset = SpotAsset(platform=platform, identifier=AssetIdentifier(value="BTC"))
        self.potential_costs[asset] = Decimal("100")

    def _update_fees(self) -> None:
        """Test implementation that adds a simple fee."""
        if self.potential_fees is None:
            self.potential_fees = []
        platform = Platform(identifier="test")
        asset = SpotAsset(platform=platform, identifier=AssetIdentifier(value="BTC"))
        fee = OperationFee(
            asset=asset,
            amount=Decimal("1"),
            fee_type=FeeType.ABSOLUTE,
            impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS,
        )
        self.potential_fees.append(fee)

    def _update_returns(self) -> None:
        """Test implementation that adds a simple return."""
        if self.potential_returns is None:
            self.potential_returns = {}
        platform = Platform(identifier="test")
        asset = SpotAsset(platform=platform, identifier=AssetIdentifier(value="BTC"))
        self.potential_returns[asset] = Decimal("110")

    def _update_totals(self) -> None:
        """Test implementation that calculates simple totals."""
        if (
            self.potential_costs is None
            or self.potential_returns is None
            or self.potential_fees is None
        ):
            return
        self.potential_total_costs = self.potential_costs.copy()
        self.potential_total_returns = {}
        for asset, amount in self.potential_returns.items():
            self.potential_total_returns[asset] = amount
            for fee in self.potential_fees:
                if (
                    fee.asset == asset
                    and fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS
                ):
                    self.potential_total_returns[asset] -= fee.amount


@pytest.fixture
def proposal() -> MockProposal:
    return MockProposal(purpose="test", client_id_prefix="TEST_")


def test_proposal_initialization(proposal: MockProposal) -> None:
    """Test that a proposal is properly initialized."""
    assert proposal.purpose == "test"
    assert proposal.client_id_prefix == "TEST_"
    assert proposal.potential_costs is None
    assert proposal.potential_returns is None
    assert proposal.potential_fees is None
    assert proposal.potential_total_costs is None
    assert proposal.potential_total_returns is None
    assert proposal.executed_operation is None


def test_proposal_initialized_property(proposal: MockProposal) -> None:
    """Test the initialized property."""
    assert not proposal.initialized
    proposal.update_proposal()
    assert proposal.initialized


def test_proposal_executed_property(proposal: MockProposal) -> None:
    """Test the executed property."""
    assert not proposal.executed
    proposal.executed_operation = MockOperation(purpose="test")
    assert proposal.executed


def test_update_proposal(proposal: MockProposal) -> None:
    """Test updating a proposal."""
    proposal.update_proposal()

    # Check that all potential values are set
    assert proposal.potential_costs is not None
    assert proposal.potential_returns is not None
    assert proposal.potential_fees is not None
    assert proposal.potential_total_costs is not None
    assert proposal.potential_total_returns is not None

    # Check specific values
    platform = Platform(identifier="test")
    asset = SpotAsset(platform=platform, identifier=AssetIdentifier(value="BTC"))

    assert proposal.potential_costs[asset] == Decimal("100")
    assert proposal.potential_returns[asset] == Decimal("110")
    assert len(proposal.potential_fees) == 1
    assert proposal.potential_fees[0].amount == Decimal("1")
    assert proposal.potential_total_costs[asset] == Decimal("100")
    assert proposal.potential_total_returns[asset] == Decimal("109")  # 110 - 1 fee


def test_update_proposal_when_executed(proposal: MockProposal) -> None:
    """Test that updating a proposal does nothing when already executed."""
    proposal.executed_operation = MockOperation(purpose="test")
    proposal.update_proposal()
    assert proposal.potential_costs is None


def test_update_proposal_error_handling(proposal: MockProposal) -> None:
    """Test that errors during update reset all potential values."""

    class ErrorProposal(MockProposal):
        def _update_costs(self) -> None:
            raise ValueError("Test error")

    error_proposal = ErrorProposal(purpose="test", client_id_prefix="TEST_")

    with pytest.raises(ValueError, match="Test error"):
        error_proposal.update_proposal()

    assert error_proposal.potential_costs is None
    assert error_proposal.potential_returns is None
    assert error_proposal.potential_fees is None
    assert error_proposal.potential_total_costs is None
    assert error_proposal.potential_total_returns is None
