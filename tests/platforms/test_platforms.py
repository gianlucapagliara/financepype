import pytest
from pydantic import ValidationError

from financepype.platforms.blockchain import BlockchainPlatform, BlockchainType
from financepype.platforms.centralized import CentralizedPlatform
from financepype.platforms.platform import Platform


def test_platform_singleton() -> None:
    """Test that Platform class implements singleton pattern correctly."""
    # Same identifier should return same instance
    platform1 = Platform(identifier="binance")
    platform2 = Platform(identifier="binance")
    assert platform1 is platform2
    assert platform1 == platform2
    assert hash(platform1) == hash(platform2)

    # Different identifiers should return different instances
    platform3 = Platform(identifier="kraken")
    assert platform1 is not platform3
    assert platform1 != platform3
    assert hash(platform1) != hash(platform3)


def test_platform_validation() -> None:
    """Test Platform validation rules."""
    # Empty identifier should raise error
    with pytest.raises(ValueError):
        Platform(identifier="")

    # None identifier should raise error
    with pytest.raises(ValidationError):
        Platform(identifier=None)  # type: ignore

    # Valid identifier should work
    platform = Platform(identifier="binance")
    assert platform.identifier == "binance"
    assert str(platform) == "binance"
    assert repr(platform) == "<Platform: binance>"


def test_centralized_platform_basic() -> None:
    """Test basic CentralizedPlatform functionality."""
    # Test without sub-identifier
    platform = CentralizedPlatform(identifier="binance")
    assert platform.identifier == "binance"
    assert platform.sub_identifier is None

    # Test with sub-identifier
    platform_with_sub = CentralizedPlatform(
        identifier="binance", sub_identifier="futures"
    )
    assert platform_with_sub.identifier == "binance"
    assert platform_with_sub.sub_identifier == "futures"


def test_centralized_platform_singleton() -> None:
    """Test that CentralizedPlatform maintains singleton behavior."""
    # Same identifier and sub-identifier should return same instance
    platform1 = CentralizedPlatform(identifier="binance", sub_identifier="futures")
    platform2 = CentralizedPlatform(identifier="binance", sub_identifier="futures")
    assert platform1 is platform2

    # Same identifier but different sub-identifier should return different instances
    platform3 = CentralizedPlatform(identifier="binance", sub_identifier="spot")
    assert platform1 is not platform3


def test_blockchain_type_values() -> None:
    """Test BlockchainType enum values."""
    assert BlockchainType.EVM.value == "EVM"
    assert BlockchainType.SOLANA.value == "Solana"


def test_blockchain_platform_basic() -> None:
    """Test basic BlockchainPlatform functionality."""
    # Test EVM platform
    eth_platform = BlockchainPlatform(identifier="ethereum", type=BlockchainType.EVM)
    assert eth_platform.identifier == "ethereum"
    assert eth_platform.type == BlockchainType.EVM

    # Test Solana platform
    sol_platform = BlockchainPlatform(identifier="solana", type=BlockchainType.SOLANA)
    assert sol_platform.identifier == "solana"
    assert sol_platform.type == BlockchainType.SOLANA


def test_blockchain_platform_validation() -> None:
    """Test BlockchainPlatform validation rules."""
    # Missing type should raise error
    with pytest.raises(ValidationError):
        BlockchainPlatform(identifier="ethereum")  # type: ignore

    # Invalid type should raise error
    with pytest.raises(ValidationError):
        BlockchainPlatform(
            identifier="ethereum",
            type="invalid",  # type: ignore
        )


def test_blockchain_platform_singleton() -> None:
    """Test that BlockchainPlatform maintains singleton behavior."""
    # Same identifier and type should return same instance
    platform1 = BlockchainPlatform(identifier="ethereum", type=BlockchainType.EVM)
    platform2 = BlockchainPlatform(identifier="ethereum", type=BlockchainType.EVM)
    assert platform1 is platform2

    # Different identifiers should return different instances
    platform3 = BlockchainPlatform(identifier="bsc", type=BlockchainType.EVM)
    assert platform1 is not platform3

    # Same identifier but different types should return different instances
    # (This shouldn't happen in practice, but testing the behavior)
    platform4 = BlockchainPlatform(identifier="ethereum", type=BlockchainType.SOLANA)
    assert platform1 is not platform4


def test_platform_clear_cache() -> None:
    """Test Platform cache clearing functionality."""
    # Create some platforms
    platform1 = Platform(identifier="test1")
    platform2 = CentralizedPlatform(identifier="test2", sub_identifier="sub")
    platform3 = BlockchainPlatform(identifier="test3", type=BlockchainType.EVM)

    # Clear cache
    Platform.clear_cache()

    # Creating new instances should return different objects
    new_platform1 = Platform(identifier="test1")
    new_platform2 = CentralizedPlatform(identifier="test2", sub_identifier="sub")
    new_platform3 = BlockchainPlatform(identifier="test3", type=BlockchainType.EVM)

    assert platform1 is not new_platform1
    assert platform2 is not new_platform2
    assert platform3 is not new_platform3


def test_platform_inheritance() -> None:
    """Test that platform inheritance works correctly."""
    # CentralizedPlatform should be instance of Platform
    centralized = CentralizedPlatform(identifier="binance")
    assert isinstance(centralized, Platform)
    assert isinstance(centralized, CentralizedPlatform)

    # BlockchainPlatform should be instance of Platform
    blockchain = BlockchainPlatform(identifier="ethereum", type=BlockchainType.EVM)
    assert isinstance(blockchain, Platform)
    assert isinstance(blockchain, BlockchainPlatform)
