from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from financepype.operations.proposal import OperationProposal
from financepype.operations.transactions.transaction import BlockchainTransaction
from financepype.owners.owner import OwnerIdentifier


class TransactionProposal(OperationProposal):
    """
    A proposal for executing a blockchain transaction.

    This class represents a proposed blockchain transaction that can be executed
    through a specific wallet. It encapsulates all the necessary information
    and validation logic required to execute the transaction.

    Attributes:
        owner_identifier (OwnerIdentifier): The wallet that will execute the transaction
        executed_operation (BlockchainTransaction): The executed transaction (after execution)
    """

    owner_identifier: OwnerIdentifier
    executed_operation: BlockchainTransaction | None = None

    # === Properties ===

    @property
    def can_be_executed(self) -> bool:
        """
        Indicates whether the proposal is ready to be executed.

        Returns:
            bool: Always True for transaction proposals
        """
        return True

    @property
    @abstractmethod
    def execute_function(self) -> Callable[[], BlockchainTransaction]:
        """
        The function that will be called to execute the transaction.

        Returns:
            Callable[[], BlockchainTransaction]: A function that creates and executes the transaction
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def execute_kwargs(self) -> dict[str, Any]:
        """
        The keyword arguments to pass to the execute function.

        Returns:
            dict[str, Any]: Dictionary of arguments needed to execute the transaction
        """
        raise NotImplementedError

    # === Execution ===

    def execute(self) -> BlockchainTransaction:
        """
        Executes the proposed transaction.

        This method creates and executes a blockchain transaction using the
        specified wallet and execution parameters.

        Returns:
            BlockchainTransaction: The executed transaction

        Raises:
            ValueError: If the proposal has already been executed or cannot be executed
        """
        if self.executed:
            raise ValueError("Proposal already executed.")

        if not self.can_be_executed:
            raise ValueError("Proposal not prepared to be executed.")

        self.executed_operation = self.execute_function(**self.execute_kwargs)
        return self.executed_operation
