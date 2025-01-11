from pydantic import BaseModel

from financepype.platforms.blockchain import BlockchainPlatform


class BlockchainConfiguration(BaseModel):
    platform: BlockchainPlatform
    chain_id: int | str | None = None
    is_local: bool = False
    is_local_supported: bool = False
