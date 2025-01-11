import logging
from abc import ABC, abstractmethod

from financepype.operators.blockchains.models import BlockchainConfiguration
from financepype.platforms.blockchain import BlockchainPlatform, BlockchainType


class Blockchain(ABC):
    def __init__(self, configuration: BlockchainConfiguration) -> None:
        super().__init__()

        self._configuration = configuration

    @classmethod
    @abstractmethod
    def logger(cls) -> logging.Logger:
        raise NotImplementedError

    # === Properties ===

    @property
    def platform(self) -> BlockchainPlatform:
        return self._configuration.platform

    @property
    def name(self) -> str:
        return (
            self.platform.identifier
            if not self._configuration.is_local
            else f"Local {self.platform.identifier}"
        )

    @property
    def type(self) -> BlockchainType:
        return self._configuration.platform.type
