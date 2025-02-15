from typing import cast

from financepype.operators.blockchains.blockchain import Blockchain
from financepype.operators.factory import OperatorFactory
from financepype.operators.operator import Operator, OperatorConfiguration


class DecentralizedApplicationConfiguration(OperatorConfiguration):
    pass


class DecentralizedApplication(Operator):
    def __init__(self, configuration: DecentralizedApplicationConfiguration):
        super().__init__(configuration)

        self._blockchain = self.initialize_blockchain()

    @property
    def configuration(self) -> DecentralizedApplicationConfiguration:
        return cast(DecentralizedApplicationConfiguration, super().configuration)

    @property
    def blockchain(self) -> Blockchain:
        return self._blockchain

    def initialize_blockchain(self) -> Blockchain:
        operator = OperatorFactory.get(self.configuration.platform)
        if not isinstance(operator, Blockchain):
            raise ValueError("Operator is not a blockchain")
        return operator
