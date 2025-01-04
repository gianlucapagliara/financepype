from decimal import Decimal
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from financepype.assets.asset import Asset


class FeeImpactType(Enum):
    ADDED_TO_COSTS = "AddedToCosts"
    DEDUCTED_FROM_RETURNS = "DeductedFromReturns"


class FeeType(Enum):
    PERCENTAGE = "Percentage"
    ABSOLUTE = "Absolute"


class OperationFee(BaseModel):
    """A class representing a fee associated with an operation.

    This class contains information about a fee, including its amount,
    associated asset, type, and impact on costs or returns.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    amount: Decimal = Field(ge=0)
    asset: Asset
    fee_type: FeeType
    impact_type: FeeImpactType

    @model_validator(mode="after")
    def validate_fee(self) -> Self:
        if self.fee_type == FeeType.PERCENTAGE and self.amount > Decimal("100"):
            raise ValueError("Percentage fee cannot be greater than 100%")
        return self
