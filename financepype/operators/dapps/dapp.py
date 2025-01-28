from typing import cast

from blockchainpype.factory import BlockchainFactory
from financepype.operators.blockchains.blockchain import Blockchain
from financepype.operators.operator import Operator, OperatorConfiguration


class DecentralizedApplicationConfiguration(OperatorConfiguration):
    pass


class DecentralizedApplication(Operator):
    def __init__(self, configuration: DecentralizedApplicationConfiguration):
        super().__init__(configuration)

        self._blockchain: Blockchain = BlockchainFactory.create(
            self.configuration.platform.identifier
        )

    @property
    def configuration(self) -> DecentralizedApplicationConfiguration:
        return cast(DecentralizedApplicationConfiguration, super().configuration)

    @property
    def blockchain(self) -> Blockchain:
        return self._blockchain
