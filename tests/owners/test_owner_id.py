from financepype.owners.owner_id import OwnerIdentifier
from financepype.platforms.platform import Platform


def test_owner_identifier_init() -> None:
    platform = Platform(identifier="binance")
    owner = OwnerIdentifier(name="trader1", platform=platform)

    assert owner.name == "trader1"
    assert owner.platform == platform
    assert owner.identifier == "binance:trader1"


def test_owner_identifier_equality() -> None:
    platform1 = Platform(identifier="binance")
    platform2 = Platform(identifier="binance")
    platform3 = Platform(identifier="ftx")

    owner1 = OwnerIdentifier(name="trader1", platform=platform1)
    owner2 = OwnerIdentifier(name="trader1", platform=platform2)
    owner3 = OwnerIdentifier(name="trader1", platform=platform3)
    owner4 = OwnerIdentifier(name="trader2", platform=platform1)

    # Same name and platform should be equal
    assert owner1 == owner2
    # Different platform should not be equal
    assert owner1 != owner3
    # Different name should not be equal
    assert owner1 != owner4
    # Different type should not be equal
    assert owner1 != "not_an_owner"  # type: ignore[comparison-overlap]


def test_owner_identifier_hash() -> None:
    platform1 = Platform(identifier="binance")
    platform2 = Platform(identifier="binance")

    owner1 = OwnerIdentifier(name="trader1", platform=platform1)
    owner2 = OwnerIdentifier(name="trader1", platform=platform2)

    # Same owners should have same hash
    assert hash(owner1) == hash(owner2)

    # Can be used as dict key
    owners_dict = {owner1: "value1"}
    assert owners_dict[owner2] == "value1"

    # Can be used in sets
    owners_set = {owner1, owner2}
    assert len(owners_set) == 1


def test_owner_identifier_repr() -> None:
    platform = Platform(identifier="binance")
    owner = OwnerIdentifier(name="trader1", platform=platform)

    assert repr(owner) == "<Owner: binance:trader1>"
