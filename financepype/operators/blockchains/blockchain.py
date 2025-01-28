import logging
from abc import abstractmethod
from typing import cast

from financepype.operations.transactions.transaction import BlockchainTransaction
from financepype.operators.blockchains.identifier import BlockchainIdentifier
from financepype.operators.blockchains.models import BlockchainConfiguration
from financepype.operators.operator import Operator, OperatorProcessor
from financepype.platforms.blockchain import BlockchainPlatform, BlockchainType


class Blockchain(Operator):
    @classmethod
    @abstractmethod
    def logger(cls) -> logging.Logger:
        raise NotImplementedError

    # === Properties ===

    @property
    def platform(self) -> BlockchainPlatform:
        return cast(BlockchainPlatform, super().platform)

    @property
    def configuration(self) -> BlockchainConfiguration:
        return cast(BlockchainConfiguration, super().configuration)

    @property
    def type(self) -> BlockchainType:
        return self.platform.type

    # === Transactions ===

    @abstractmethod
    async def fetch_transaction(
        self, transaction_id: BlockchainIdentifier
    ) -> BlockchainTransaction | None:
        raise NotImplementedError


class BlockchainProcessor(OperatorProcessor): ...
