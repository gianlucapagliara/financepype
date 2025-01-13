from financepype.owners.owner_id import OwnerIdentifier
from financepype.platforms.centralized import CentralizedPlatform


class AccountIdentifier(OwnerIdentifier):
    platform: CentralizedPlatform
