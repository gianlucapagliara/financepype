from enum import Enum

from pydantic import Field

from financepype.platforms.platform import Platform


class BlockchainType(Enum):
    """Enumeration of supported blockchain types.

    This enum defines the different types of blockchain networks that
    the system can interact with. Each type represents a distinct
    blockchain ecosystem with its own protocols and characteristics.
    """

    pass


class BlockchainPlatform(Platform):
    """A platform representing a specific blockchain network.

    This class extends the base Platform class to represent blockchain-specific
    platforms. It adds blockchain type information to distinguish between
    different blockchain ecosystems.

    Attributes:
        type (BlockchainType): The type of blockchain network
        identifier (str): Inherited from Platform, identifies the specific chain

    Example:
        >>> eth_mainnet = BlockchainPlatform(identifier="ethereum", type=BlockchainType.EVM)
        >>> solana_mainnet = BlockchainPlatform(identifier="solana", type=BlockchainType.SOLANA)
    """

    type: BlockchainType
    local: bool = Field(
        default=False,
        description="Whether this is a local chain (e.g. Ganache, Hardhat, etc.)",
    )
    testnet: bool = Field(
        default=False,
        description="Whether this is a testnet chain (e.g. Sepolia, etc.)",
    )
    chain_id: int | str | None = None
