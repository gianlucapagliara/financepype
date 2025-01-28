from financepype.operators.operator import OperatorConfiguration
from financepype.platforms.blockchain import BlockchainPlatform


class BlockchainConfiguration(OperatorConfiguration):
    platform: BlockchainPlatform
