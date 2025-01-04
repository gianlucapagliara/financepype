from abc import ABC, abstractmethod
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from financepype.assets.asset import Asset
from financepype.operations.fees import OperationFee
from financepype.operations.operation import Operation


class OperationProposal(BaseModel, ABC):
    """Abstract base class for proposing trading operations.

    This class provides a framework for calculating and tracking the potential
    costs, returns, and fees of a trading operation before it is executed.
    It allows for dry-run analysis of trading operations.

    The proposal goes through several stages:
    1. Initialization with a purpose and optional client ID prefix
    2. Update of potential costs, returns, and fees
    3. Optional execution into an actual operation

    Attributes:
        purpose (str): The purpose of this operation proposal
        client_id_prefix (str): Optional prefix for client operation IDs
        potential_costs (dict[Asset, Decimal] | None): Estimated costs per asset
        potential_returns (dict[Asset, Decimal] | None): Estimated returns per asset
        potential_fees (list[OperationFee] | None): Estimated operation fees
        potential_total_costs (dict[Asset, Decimal] | None): Total costs including fees
        potential_total_returns (dict[Asset, Decimal] | None): Total returns after fees
        executed_operation (Operation | None): The executed operation if any
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    purpose: str
    client_id_prefix: str = ""
    potential_costs: dict[Asset, Decimal] | None = None
    potential_returns: dict[Asset, Decimal] | None = None
    potential_fees: list[OperationFee] | None = None
    potential_total_costs: dict[Asset, Decimal] | None = None
    potential_total_returns: dict[Asset, Decimal] | None = None
    executed_operation: Operation | None = None

    @property
    def initialized(self) -> bool:
        """Check if the proposal has been initialized with potential values.

        Returns:
            bool: True if potential costs have been calculated
        """
        return self.potential_costs is not None

    @property
    def executed(self) -> bool:
        """Check if the proposal has been executed.

        Returns:
            bool: True if an operation has been created from this proposal
        """
        return self.executed_operation is not None

    def update_proposal(self) -> None:
        """Update the proposal's potential costs, returns, and fees.

        This method orchestrates the update process by:
        1. Preparing for the update
        2. Calculating potential costs
        3. Calculating potential fees
        4. Calculating potential returns
        5. Calculating total costs and returns

        If any step fails, all potential values are reset to None.

        Raises:
            Exception: If any update step fails
        """
        if self.executed:
            return

        self._prepare_update()

        self.potential_costs = {}
        self.potential_returns = {}
        self.potential_fees = []

        try:
            self._update_costs()
            self._update_fees()
            self._update_returns()
            self._update_totals()
        except Exception as e:
            self.potential_costs = None
            self.potential_returns = None
            self.potential_fees = None
            self.potential_total_costs = None
            self.potential_total_returns = None
            raise e

    @abstractmethod
    def _prepare_update(self) -> None:
        """Prepare for updating the proposal.

        This method should perform any necessary setup before
        calculating costs, fees, and returns.

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def _update_costs(self) -> None:
        """Calculate the potential costs of the operation.

        This method should update self.potential_costs with a mapping
        of assets to their estimated costs.

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def _update_fees(self) -> None:
        """Calculate the potential fees for the operation.

        This method should update self.potential_fees with a list
        of estimated operation fees.

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def _update_returns(self) -> None:
        """Calculate the potential returns from the operation.

        This method should update self.potential_returns with a mapping
        of assets to their estimated returns.

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def _update_totals(self) -> None:
        """Calculate the total costs and returns including fees.

        This method should update self.potential_total_costs and
        self.potential_total_returns with the final estimates.

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
