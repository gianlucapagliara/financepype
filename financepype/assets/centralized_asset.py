from financepype.assets.asset import Asset
from financepype.assets.asset_id import AssetIdentifier


class CentralizedAsset(Asset):
    """
    Centralized asset
    """

    identifier: AssetIdentifier

    @property
    def symbol(self) -> str:
        return self.identifier.value
