from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from financepype.assets.asset import Asset
from financepype.assets.asset_id import AssetIdentifier
from financepype.operators.blockchains.identifier import BlockchainIdentifier


class BlockchainAssetIdentifier(AssetIdentifier):
    """Identifier specific to blockchain assets.

    Extends the base AssetIdentifier to include blockchain-specific identification.

    Attributes:
        identifier (BlockchainIdentifier): The blockchain-specific identifier
    """

    identifier: BlockchainIdentifier


class BlockchainAssetData(BaseModel):
    """Data specific to blockchain assets.

    This class holds the mutable data specific to blockchain assets.
    It is separated from the immutable BlockchainAsset class to maintain
    proper immutability semantics.

    Attributes:
        name (str): The full name of the asset
        symbol (str): The trading symbol of the asset
        decimals (int): Number of decimal places the asset uses
    """

    name: str
    symbol: str
    decimals: int


class BlockchainAsset(Asset):
    """Base class for blockchain-based assets.

    This class represents assets that exist on a blockchain, such as tokens or coins.
    It provides common functionality for interacting with blockchain assets including
    balance queries, approvals, and transfers.

    Attributes:
        identifier (BlockchainAssetIdentifier): The blockchain-specific asset identifier
        data (BlockchainAssetData): The blockchain-specific asset data
    """

    model_config = ConfigDict(frozen=True)

    identifier: BlockchainAssetIdentifier
    data: BlockchainAssetData

    def convert_to_decimals(self, raw_amount: int) -> Decimal:
        """Convert raw token units to decimal representation.

        Args:
            raw_amount (int): The raw amount in smallest token units

        Returns:
            Decimal: The amount converted to decimal representation
        """
        return Decimal(raw_amount) / Decimal(10**self.data.decimals)

    def convert_to_raw(self, decimal_amount: Decimal) -> int:
        """Convert decimal amount to raw token units.

        Args:
            decimal_amount (Decimal): The amount in decimal representation

        Returns:
            int: The amount converted to raw token units
        """
        return int(decimal_amount * 10**self.data.decimals)
