from decimal import Decimal

import pytest

from financepype.assets.asset import Asset
from financepype.assets.spot import SpotAsset
from financepype.owners.owner import Owner, OwnerConfiguration, OwnerIdentifier
from financepype.platforms.platform import Platform


class MockOwner(Owner):
    """Mock owner class for testing that implements the required abstract methods."""

    pass


@pytest.fixture
def owner_id(platform: Platform) -> OwnerIdentifier:
    return OwnerIdentifier(name="test_trader", platform=platform)


@pytest.fixture
def owner(owner_id: OwnerIdentifier) -> Owner:
    return MockOwner(configuration=OwnerConfiguration(identifier=owner_id))


def test_owner_init(owner: Owner, owner_id: OwnerIdentifier) -> None:
    assert owner.identifier == owner_id
    assert owner.platform.identifier == "test_platform"
    assert owner.balance_tracker is not None


def test_owner_get_balances(
    owner: Owner, btc_asset: SpotAsset, usdt_asset: SpotAsset
) -> None:
    # Test initial balances
    assert owner.get_balance("BTC") == Decimal("0")
    assert owner.get_available_balance("BTC") == Decimal("0")

    # Set some balances
    total_balances: list[tuple[Asset, Decimal]] = [
        (btc_asset, Decimal("1.5")),
        (usdt_asset, Decimal("1000")),
    ]
    available_balances: list[tuple[Asset, Decimal]] = [
        (btc_asset, Decimal("1.0")),
        (usdt_asset, Decimal("800")),
    ]

    updated_total, updated_available = owner.set_balances(
        total_balances=total_balances,
        available_balances=available_balances,
        complete_snapshot=True,
    )

    # Check updated balances
    assert owner.get_balance("BTC") == Decimal("1.5")
    assert owner.get_available_balance("BTC") == Decimal("1.0")
    assert owner.get_balance("USDT") == Decimal("1000")
    assert owner.get_available_balance("USDT") == Decimal("800")

    # Check returned updated balances
    assert updated_total == {"BTC": Decimal("1.5"), "USDT": Decimal("1000")}
    assert updated_available == {"BTC": Decimal("1.0"), "USDT": Decimal("800")}


def test_owner_get_all_balances(
    owner: Owner, btc_asset: SpotAsset, usdt_asset: SpotAsset
) -> None:
    # Set some balances
    total_balances: list[tuple[Asset, Decimal]] = [
        (btc_asset, Decimal("1.5")),
        (usdt_asset, Decimal("1000")),
    ]
    available_balances: list[tuple[Asset, Decimal]] = [
        (btc_asset, Decimal("1.0")),
        (usdt_asset, Decimal("800")),
    ]

    owner.set_balances(
        total_balances=total_balances,
        available_balances=available_balances,
        complete_snapshot=True,
    )

    # Test get_all_balances
    all_balances = owner.get_all_balances()
    assert all_balances == {"BTC": Decimal("1.5"), "USDT": Decimal("1000")}

    # Test get_all_available_balances
    all_available = owner.get_all_available_balances()
    assert all_available == {"BTC": Decimal("1.0"), "USDT": Decimal("800")}
