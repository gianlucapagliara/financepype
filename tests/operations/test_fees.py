from decimal import Decimal

import pytest
from pydantic import ValidationError

from financepype.assets.spot import SpotAsset
from financepype.operations.fees import FeeImpactType, FeeType, OperationFee


def test_operation_fee_initialization(test_asset: SpotAsset) -> None:
    """Test basic initialization of operation fees."""
    # Test percentage fee
    percentage_fee = OperationFee(
        amount=Decimal("0.1"),
        asset=test_asset,
        fee_type=FeeType.PERCENTAGE,
        impact_type=FeeImpactType.ADDED_TO_COSTS,
    )
    assert percentage_fee.amount == Decimal("0.1")
    assert percentage_fee.asset == test_asset
    assert percentage_fee.fee_type == FeeType.PERCENTAGE
    assert percentage_fee.impact_type == FeeImpactType.ADDED_TO_COSTS

    # Test absolute fee
    absolute_fee = OperationFee(
        amount=Decimal("10"),
        asset=test_asset,
        fee_type=FeeType.ABSOLUTE,
        impact_type=FeeImpactType.DEDUCTED_FROM_RETURNS,
    )
    assert absolute_fee.amount == Decimal("10")
    assert absolute_fee.asset == test_asset
    assert absolute_fee.fee_type == FeeType.ABSOLUTE
    assert absolute_fee.impact_type == FeeImpactType.DEDUCTED_FROM_RETURNS


def test_operation_fee_validation(test_asset: SpotAsset) -> None:
    """Test fee validation rules."""
    # Test valid percentage fee
    valid_percentage = OperationFee(
        amount=Decimal("100"),
        asset=test_asset,
        fee_type=FeeType.PERCENTAGE,
        impact_type=FeeImpactType.ADDED_TO_COSTS,
    )
    assert valid_percentage.amount == Decimal("100")

    # Test invalid percentage fee (>100%)
    with pytest.raises(ValidationError):
        OperationFee(
            amount=Decimal("101"),
            asset=test_asset,
            fee_type=FeeType.PERCENTAGE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        )

    # Test invalid negative fee
    with pytest.raises(ValidationError):
        OperationFee(
            amount=Decimal("-1"),
            asset=test_asset,
            fee_type=FeeType.ABSOLUTE,
            impact_type=FeeImpactType.ADDED_TO_COSTS,
        )


def test_fee_impact_types() -> None:
    """Test fee impact type enumeration."""
    assert FeeImpactType.ADDED_TO_COSTS.value == "AddedToCosts"
    assert FeeImpactType.DEDUCTED_FROM_RETURNS.value == "DeductedFromReturns"


def test_fee_types() -> None:
    """Test fee type enumeration."""
    assert FeeType.PERCENTAGE.value == "Percentage"
    assert FeeType.ABSOLUTE.value == "Absolute"
