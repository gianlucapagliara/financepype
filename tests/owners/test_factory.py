import pytest

from financepype.assets.asset import Asset
from financepype.owners.factory import OwnerFactory
from financepype.owners.owner import Owner, OwnerConfiguration, OwnerIdentifier
from financepype.platforms.platform import Platform


class MockOwner(Owner):
    """A test owner implementation with a test-specific value."""

    def __init__(self, configuration: OwnerConfiguration) -> None:
        super().__init__(configuration)
        # Test-specific attribute
        self._test_value = 0

    @property
    def test_value(self) -> int:
        """Test-specific property."""
        return self._test_value

    @property
    def current_timestamp(self) -> float:
        return 0.0

    async def update_all_balances(self) -> None:
        pass

    async def update_all_positions(self) -> None:
        pass

    async def update_balance(self, asset: Asset) -> None:
        pass


class AnotherMockOwner(Owner):
    """Another test owner implementation with a test-specific value."""

    def __init__(self, configuration: OwnerConfiguration) -> None:
        super().__init__(configuration)
        # Test-specific attribute
        self._test_value = 1

    @property
    def test_value(self) -> int:
        """Test-specific property."""
        return self._test_value

    @property
    def current_timestamp(self) -> float:
        return 1.0

    async def update_all_balances(self) -> None:
        pass

    async def update_all_positions(self) -> None:
        pass

    async def update_balance(self, asset: Asset) -> None:
        pass


@pytest.fixture
def platform() -> Platform:
    """Fixture providing a test platform."""
    return Platform(identifier="test")


@pytest.fixture
def identifier(platform: Platform) -> OwnerIdentifier:
    """Fixture providing a test owner identifier."""
    return OwnerIdentifier(platform=platform, name="test_owner")


@pytest.fixture
def config(identifier: OwnerIdentifier) -> OwnerConfiguration:
    """Fixture providing a test configuration."""
    return OwnerConfiguration(identifier=identifier)


@pytest.fixture(autouse=True)
def reset_factory() -> None:
    """Reset the factory before each test."""
    OwnerFactory.reset()


def test_owner_singleton(
    platform: Platform, identifier: OwnerIdentifier, config: OwnerConfiguration
) -> None:
    """Test that owners are properly cached as singletons."""
    # Register owner class and configuration
    OwnerFactory.register_owner_class(platform, MockOwner)
    OwnerFactory.register_configuration(config)

    # Same identifier should return same instance
    owner1 = OwnerFactory.get(identifier)
    owner2 = OwnerFactory.get(identifier)
    assert owner1 is owner2

    # Different identifier should return different instance
    platform2 = Platform(identifier="test2")
    identifier2 = OwnerIdentifier(platform=platform2, name="test_owner2")
    config2 = OwnerConfiguration(identifier=identifier2)
    OwnerFactory.register_owner_class(platform2, MockOwner)
    OwnerFactory.register_configuration(config2)
    owner3 = OwnerFactory.get(identifier2)
    assert owner1 is not owner3


def test_owner_class_registration(
    platform: Platform, identifier: OwnerIdentifier
) -> None:
    """Test owner class registration."""
    # Register owner class
    OwnerFactory.register_owner_class(platform, MockOwner)

    # Duplicate registration should fail
    with pytest.raises(ValueError):
        OwnerFactory.register_owner_class(platform, MockOwner)

    # Creating owner without registration should fail
    unknown_platform = Platform(identifier="unknown")
    unknown_identifier = OwnerIdentifier(platform=unknown_platform, name="unknown")
    with pytest.raises(ValueError) as exc_info:
        OwnerFactory.get(unknown_identifier)
    assert "No configuration registered for" in str(exc_info.value)


def test_owner_cache_management(
    platform: Platform, identifier: OwnerIdentifier, config: OwnerConfiguration
) -> None:
    """Test cache management functions."""
    # Register owner class and configuration
    OwnerFactory.register_owner_class(platform, MockOwner)
    OwnerFactory.register_configuration(config)

    # Create owner
    owner = OwnerFactory.get(identifier)
    assert OwnerFactory.get_cache_info()["cache_size"] == 1

    # Clear cache
    OwnerFactory.clear_cache()
    assert OwnerFactory.get_cache_info()["cache_size"] == 0

    # New request should create new instance
    owner2 = OwnerFactory.get(identifier)
    assert owner is not owner2


def test_configuration_registration(
    platform: Platform, identifier: OwnerIdentifier, config: OwnerConfiguration
) -> None:
    """Test configuration registration and retrieval."""
    # Register owner class
    OwnerFactory.register_owner_class(platform, MockOwner)

    # Register configuration
    OwnerFactory.register_configuration(config)

    # Get configuration
    retrieved_config = OwnerFactory.get_configuration(identifier)
    assert retrieved_config == config

    # List configurations
    configs = OwnerFactory.list_configurations()
    assert identifier in configs
    assert configs[identifier] == config

    # Duplicate registration should fail
    with pytest.raises(ValueError):
        OwnerFactory.register_configuration(config)

    # Registration without owner class should fail
    unknown_platform = Platform(identifier="unknown")
    unknown_identifier = OwnerIdentifier(platform=unknown_platform, name="unknown")
    config2 = OwnerConfiguration(identifier=unknown_identifier)
    with pytest.raises(ValueError):
        OwnerFactory.register_configuration(config2)

    # Non-existent configuration
    assert OwnerFactory.get_configuration(unknown_identifier) is None


def test_get_with_missing_config(identifier: OwnerIdentifier) -> None:
    """Test getting an owner with a non-existent configuration."""
    with pytest.raises(ValueError) as exc_info:
        OwnerFactory.get(identifier)
    assert "No configuration registered for" in str(exc_info.value)


def test_owner_reset(
    platform: Platform, identifier: OwnerIdentifier, config: OwnerConfiguration
) -> None:
    """Test complete factory reset."""
    # Setup factory
    OwnerFactory.register_owner_class(platform, MockOwner)
    OwnerFactory.register_configuration(config)
    _ = OwnerFactory.get(identifier)

    assert OwnerFactory.get_cache_info()["cache_size"] > 0
    assert OwnerFactory.get_cache_info()["registered_owner_classes"] > 0
    assert OwnerFactory.get_cache_info()["registered_configurations"] > 0

    # Reset factory
    OwnerFactory.reset()

    assert OwnerFactory.get_cache_info()["cache_size"] == 0
    assert OwnerFactory.get_cache_info()["registered_owner_classes"] == 0
    assert OwnerFactory.get_cache_info()["registered_configurations"] == 0


def test_owner_type_safety(
    platform: Platform, identifier: OwnerIdentifier, config: OwnerConfiguration
) -> None:
    """Test that owners are returned with correct type."""
    # Register and get owner
    OwnerFactory.register_owner_class(platform, MockOwner)
    OwnerFactory.register_configuration(config)
    owner = OwnerFactory.get(identifier)

    # Verify type
    assert isinstance(owner, MockOwner)
    assert isinstance(owner, Owner)


def test_cache_key_uniqueness(
    platform: Platform, identifier: OwnerIdentifier, config: OwnerConfiguration
) -> None:
    """Test that cache keys are unique for different owner classes."""
    # First owner
    OwnerFactory.register_owner_class(platform, MockOwner)
    OwnerFactory.register_configuration(config)
    owner1 = OwnerFactory.get(identifier)

    # Clear and register different owner class
    OwnerFactory.reset()

    OwnerFactory.register_owner_class(platform, AnotherMockOwner)
    OwnerFactory.register_configuration(config)
    owner2 = OwnerFactory.get(identifier)

    # Verify different types and behavior
    assert type(owner1) is not type(owner2)
    assert owner1.test_value == 0  # type: ignore
    assert owner2.test_value == 1  # type: ignore


def test_configuration_immutability(
    platform: Platform, identifier: OwnerIdentifier, config: OwnerConfiguration
) -> None:
    """Test that returned configurations are copies."""
    # Register configuration
    OwnerFactory.register_owner_class(platform, MockOwner)
    OwnerFactory.register_configuration(config)

    # Try to modify returned configurations
    configs = OwnerFactory.list_configurations()
    modified_platform = Platform(identifier="modified")
    modified_identifier = OwnerIdentifier(platform=modified_platform, name="modified")
    modified_config = OwnerConfiguration(identifier=modified_identifier)
    configs[identifier] = modified_config

    # Verify original is unchanged
    original_config = OwnerFactory.get_configuration(identifier)
    assert original_config is not None
    assert original_config == config
    assert original_config.identifier.platform.identifier == "test"
    assert original_config.identifier.name == "test_owner"

    # Verify get returns same as original
    retrieved_config = OwnerFactory.get_configuration(identifier)
    assert retrieved_config is not None
    assert retrieved_config.identifier == identifier


def test_multiple_owners_per_platform(platform: Platform) -> None:
    """Test that multiple owners can exist for the same platform."""
    # Create two different owners for the same platform
    identifier1 = OwnerIdentifier(platform=platform, name="owner1")
    identifier2 = OwnerIdentifier(platform=platform, name="owner2")
    config1 = OwnerConfiguration(identifier=identifier1)
    config2 = OwnerConfiguration(identifier=identifier2)

    # Register class and configurations
    OwnerFactory.register_owner_class(platform, MockOwner)
    OwnerFactory.register_configuration(config1)
    OwnerFactory.register_configuration(config2)

    # Get both owners
    owner1 = OwnerFactory.get(identifier1)
    owner2 = OwnerFactory.get(identifier2)

    # Verify they are different instances
    assert owner1 is not owner2
    assert owner1.identifier.name == "owner1"
    assert owner2.identifier.name == "owner2"
    assert owner1.identifier.platform is owner2.identifier.platform
