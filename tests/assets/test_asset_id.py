import pytest
from pydantic import ValidationError

from financepype.assets.asset_id import AssetIdentifier


def test_asset_identifier_creation() -> None:
    identifier = AssetIdentifier(value="BTC")
    assert str(identifier) == "BTC"
    assert identifier.value == "BTC"


def test_asset_identifier_immutability() -> None:
    identifier = AssetIdentifier(value="BTC")
    with pytest.raises(ValidationError):
        identifier.value = "ETH"


def test_asset_identifier_equality() -> None:
    id1 = AssetIdentifier(value="BTC")
    id2 = AssetIdentifier(value="BTC")
    id3 = AssetIdentifier(value="ETH")

    assert id1 == id2
    assert id1 != id3
    assert id1 != "BTC"  # Different type


def test_asset_identifier_hash() -> None:
    id1 = AssetIdentifier(value="BTC")
    id2 = AssetIdentifier(value="BTC")

    # Same value should have same hash
    assert hash(id1) == hash(id2)

    # Can be used as dict key
    d = {id1: "value"}
    assert d[id2] == "value"
