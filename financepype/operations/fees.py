from decimal import Decimal
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, model_validator

from financepype.assets.asset import Asset


class FeeImpactType(Enum):
    """Enumeration of how fees impact operation costs.

    - ADDED_TO_COSTS: Fee is added to the operation cost
    - DEDUCTED_FROM_RETURNS: Fee is subtracted from operation returns
    """

    ADDED_TO_COSTS = "AddedToCosts"
    DEDUCTED_FROM_RETURNS = "DeductedFromReturns"


class FeeType(Enum):
    """Enumeration of fee calculation methods.

    - PERCENTAGE: Fee is calculated as a percentage of the operation amount
    - ABSOLUTE: Fee is a fixed amount
    """

    PERCENTAGE = "Percentage"
    ABSOLUTE = "Absolute"


class OperationFee(BaseModel):
    """A class representing a fee associated with an operation.

    This class models fees charged for trading operations, supporting both
    percentage-based and absolute fee amounts, and tracking how the fee
    impacts the operation's costs or returns.

    Attributes:
        amount (Decimal): Fee amount (percentage or absolute value)
        asset (Asset | None): Asset in which the fee is denominated
        fee_type (FeeType): How the fee is calculated (percentage/absolute)
        impact_type (FeeImpactType): How the fee impacts costs/returns

    Example:
        >>> fee = OperationFee(
        ...     amount=Decimal("0.1"),
        ...     asset=btc_asset,
        ...     fee_type=FeeType.PERCENTAGE,
        ...     impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS
        ... )
    """

    amount: Decimal = Field(ge=0)
    asset: Asset | None = None
    fee_type: FeeType
    impact_type: FeeImpactType

    @model_validator(mode="after")
    def validate_fee(self) -> Self:
        """Validate fee amount based on fee type.

        Ensures that percentage fees do not exceed 100%.

        Returns:
            Self: The validated instance

        Raises:
            ValueError: If a percentage fee is greater than 100%
        """
        if self.fee_type == FeeType.PERCENTAGE and self.amount > Decimal("100"):
            raise ValueError("Percentage fee cannot be greater than 100%")
        return self
