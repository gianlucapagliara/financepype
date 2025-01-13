from pydantic import Field

from financepype.platforms.platform import Platform


class CentralizedPlatform(Platform):
    """A centralized platform that is a single entity.

    Attributes:
        sub_identifier (str | None): The sub-identifier for the platform
    """

    sub_identifier: str | None = Field(
        default=None,
        description="The sub-identifier for the platform",
    )
    domain: str | None = Field(
        default=None,
        description="The domain for the platform",
    )
