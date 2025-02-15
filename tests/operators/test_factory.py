import pytest

from financepype.operators.factory import OperatorFactory
from financepype.operators.operator import Operator, OperatorConfiguration
from financepype.platforms.platform import Platform


class MockOperator(Operator):
    """A test operator implementation."""

    @property
    def current_timestamp(self) -> float:
        return 0.0


@pytest.fixture
def platform() -> Platform:
    """Fixture providing a test platform."""
    return Platform(identifier="test")


@pytest.fixture
def config(platform: Platform) -> OperatorConfiguration:
    """Fixture providing a test configuration."""
    return OperatorConfiguration(platform=platform)


def test_operator_singleton(platform: Platform, config: OperatorConfiguration) -> None:
    """Test that operators are properly cached as singletons."""
    # Register operator class and configuration
    OperatorFactory.register_operator_class(platform, MockOperator)
    OperatorFactory.register_configuration(platform, config)

    # Same platform should return same instance
    operator1 = OperatorFactory.get(platform)
    operator2 = OperatorFactory.get(platform)
    assert operator1 is operator2

    # Different platform should return different instance
    platform2 = Platform(identifier="test2")
    config2 = OperatorConfiguration(platform=platform2)
    OperatorFactory.register_operator_class(platform2, MockOperator)
    OperatorFactory.register_configuration(platform2, config2)
    operator3 = OperatorFactory.get(platform2)
    assert operator1 is not operator3


def test_operator_class_registration(platform: Platform) -> None:
    """Test operator class registration."""
    # Register operator class
    OperatorFactory.register_operator_class(platform, MockOperator)

    # Duplicate registration should fail
    with pytest.raises(ValueError):
        OperatorFactory.register_operator_class(platform, MockOperator)

    # Creating operator without registration should fail
    unknown_platform = Platform(identifier="unknown")
    with pytest.raises(ValueError) as exc_info:
        OperatorFactory.get(unknown_platform)
    assert "No configuration registered for platform" in str(exc_info.value)


def test_operator_cache_management(
    platform: Platform, config: OperatorConfiguration
) -> None:
    """Test cache management functions."""
    # Register operator class and configuration
    OperatorFactory.register_operator_class(platform, MockOperator)
    OperatorFactory.register_configuration(platform, config)

    # Create operator
    operator = OperatorFactory.get(platform)
    assert OperatorFactory.get_cache_info()["cache_size"] == 1

    # Clear cache
    OperatorFactory.clear_cache()
    assert OperatorFactory.get_cache_info()["cache_size"] == 0

    # New request should create new instance
    operator2 = OperatorFactory.get(platform)
    assert operator is not operator2


def test_configuration_registration(
    platform: Platform, config: OperatorConfiguration
) -> None:
    """Test configuration registration and retrieval."""
    # Register operator class
    OperatorFactory.register_operator_class(platform, MockOperator)

    # Register configuration
    OperatorFactory.register_configuration(platform, config)

    # Get configuration
    retrieved_config = OperatorFactory.get_configuration(platform)
    assert retrieved_config == config

    # List configurations
    configs = OperatorFactory.list_configurations()
    assert platform in configs
    assert configs[platform] == config

    # Duplicate registration should fail
    with pytest.raises(ValueError):
        OperatorFactory.register_configuration(platform, config)

    # Registration without operator class should fail
    unknown_platform = Platform(identifier="unknown")
    config2 = OperatorConfiguration(platform=unknown_platform)
    with pytest.raises(ValueError):
        OperatorFactory.register_configuration(unknown_platform, config2)

    # Configuration platform must match registration platform
    mismatched_platform = Platform(identifier="mismatched")
    mismatched_config = OperatorConfiguration(platform=platform)
    with pytest.raises(ValueError) as exc_info:
        OperatorFactory.register_configuration(mismatched_platform, mismatched_config)
    assert "Configuration platform" in str(exc_info.value)

    # Non-existent configuration
    assert OperatorFactory.get_configuration(unknown_platform) is None


def test_get_with_missing_config(platform: Platform) -> None:
    """Test getting an operator with a non-existent configuration."""
    with pytest.raises(ValueError) as exc_info:
        OperatorFactory.get(platform)
    assert "No configuration registered for platform" in str(exc_info.value)


def test_operator_reset(platform: Platform, config: OperatorConfiguration) -> None:
    """Test complete factory reset."""
    # Setup factory
    OperatorFactory.register_operator_class(platform, MockOperator)
    OperatorFactory.register_configuration(platform, config)
    operator = OperatorFactory.get(platform)

    assert OperatorFactory.get_cache_info()["cache_size"] > 0
    assert OperatorFactory.get_cache_info()["registered_operator_classes"] > 0
    assert OperatorFactory.get_cache_info()["registered_configurations"] > 0

    # Reset factory
    OperatorFactory.reset()

    assert OperatorFactory.get_cache_info()["cache_size"] == 0
    assert OperatorFactory.get_cache_info()["registered_operator_classes"] == 0
    assert OperatorFactory.get_cache_info()["registered_configurations"] == 0


def test_operator_type_safety(
    platform: Platform, config: OperatorConfiguration
) -> None:
    """Test that operators are returned with correct type."""
    # Register and get operator
    OperatorFactory.register_operator_class(platform, MockOperator)
    OperatorFactory.register_configuration(platform, config)
    operator = OperatorFactory.get(platform)

    # Verify type
    assert isinstance(operator, MockOperator)
    assert isinstance(operator, Operator)


def test_cache_key_uniqueness(
    platform: Platform, config: OperatorConfiguration
) -> None:
    """Test that cache keys are unique for different operator classes."""

    class AnotherMockOperator(Operator):
        """Another test operator implementation."""

        @property
        def current_timestamp(self) -> float:
            return 1.0  # Different from MockOperator

    # First operator
    OperatorFactory.register_operator_class(platform, MockOperator)
    OperatorFactory.register_configuration(platform, config)
    operator1 = OperatorFactory.get(platform)

    # Clear and register different operator class
    OperatorFactory.reset()

    OperatorFactory.register_operator_class(platform, AnotherMockOperator)
    OperatorFactory.register_configuration(platform, config)
    operator2 = OperatorFactory.get(platform)

    # Verify different types and behavior
    assert type(operator1) is not type(operator2)
    assert operator1.current_timestamp == 0.0
    assert operator2.current_timestamp == 1.0


def test_configuration_immutability(
    platform: Platform, config: OperatorConfiguration
) -> None:
    """Test that returned configurations are copies."""
    # Register configuration
    OperatorFactory.register_operator_class(platform, MockOperator)
    OperatorFactory.register_configuration(platform, config)

    # Try to modify returned configurations
    configs = OperatorFactory.list_configurations()
    modified_platform = Platform(identifier="modified")
    configs[platform] = OperatorConfiguration(platform=modified_platform)

    # Verify original is unchanged
    original_config = OperatorFactory.get_configuration(platform)
    assert original_config is not None
    assert original_config == config
    assert original_config.platform.identifier == "test"

    # Verify get returns same as original
    retrieved_config = OperatorFactory.get_configuration(platform)
    assert retrieved_config is not None  # Narrow type for mypy
    assert retrieved_config.platform == platform
