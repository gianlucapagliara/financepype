from typing import TypeVar

from financepype.owners.owner import Owner, OwnerConfiguration, OwnerIdentifier
from financepype.platforms.platform import Platform

T = TypeVar("T", bound=Owner)


class OwnerFactory:
    """Factory class for creating and caching owner instances.

    This class provides a centralized way to create and manage owner instances.
    It uses a global cache to ensure that the same owner (identified by platform and name)
    always returns the same instance, which is crucial for maintaining state and memory efficiency.

    The primary way to use the factory is through configurations:
    1. Register owner classes for platforms
    2. Register configurations
    3. Get owners using configurations

    Example:
        >>> platform = Platform(identifier="binance")
        >>> OwnerFactory.register_owner_class(platform, Account)
        >>> config = AccountConfiguration(identifier=AccountIdentifier(...))
        >>> OwnerFactory.register_configuration(config)
        >>> owner1 = OwnerFactory.get(config.identifier)
        >>> owner2 = OwnerFactory.get(config.identifier)
        >>> assert owner1 is owner2  # Same instance
    """

    _platform_class_mapping: dict[Platform, type[Owner]] = {}
    _configurations: dict[OwnerIdentifier, OwnerConfiguration] = {}
    _cache: dict[OwnerIdentifier, Owner] = {}

    @classmethod
    def reset(cls) -> None:
        """Reset the factory to its initial state.

        This method:
        1. Clears the owner cache
        2. Clears registered owner classes
        3. Clears registered configurations

        Useful for testing or when a complete reset is needed.
        """
        cls._cache.clear()
        cls._platform_class_mapping.clear()
        cls._configurations.clear()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear only the owner cache, keeping registrations intact."""
        cls._cache.clear()

    @classmethod
    def get_cache_info(cls) -> dict[str, int]:
        """Get information about the current cache state.

        Returns:
            dict with cache statistics including:
            - cache_size: Number of cached owners
            - registered_owner_classes: Number of registered owner classes
            - registered_configurations: Number of registered configurations
        """
        return {
            "cache_size": len(cls._cache),
            "registered_owner_classes": len(cls._platform_class_mapping),
            "registered_configurations": len(cls._configurations),
        }

    @classmethod
    def register_owner_class(cls, platform: Platform, owner_class: type[Owner]) -> None:
        """Register an owner class for a platform.

        This associates a specific owner implementation with a platform.
        When creating owners, the factory will automatically use the correct class
        based on the platform.

        Args:
            platform: The platform to register for
            owner_class: The owner class to use for this platform

        Raises:
            ValueError: If a class is already registered for this platform
        """
        if platform in cls._platform_class_mapping:
            raise ValueError(
                f"Owner class already registered for platform '{platform}'"
            )
        cls._platform_class_mapping[platform] = owner_class

    @classmethod
    def register_configuration(cls, configuration: OwnerConfiguration) -> None:
        """Register a configuration.

        This is the primary way to register configurations in the factory.
        Each platform-name combination can have only one configuration at a time.

        Args:
            configuration: The owner configuration to register

        Raises:
            ValueError: If a configuration already exists for this platform and name
            ValueError: If no owner class is registered for the platform
        """
        identifier = configuration.identifier

        if identifier in cls._configurations:
            raise ValueError(f"Configuration already registered for {identifier}")

        if identifier.platform not in cls._platform_class_mapping:
            raise ValueError(
                f"No owner class registered for platform '{identifier.platform}'. "
                "Register a class first using register_owner_class()"
            )

        cls._configurations[identifier] = configuration

    @classmethod
    def get(cls, identifier: OwnerIdentifier) -> Owner:
        """Get or create an owner instance for a given identifier.

        This is the primary way to get owner instances from the factory.
        The owner class and configuration are automatically determined from the identifier.

        Args:
            identifier: The owner identifier to get an instance for

        Returns:
            The owner instance

        Raises:
            ValueError: If no configuration is registered for the identifier
        """
        config = cls._configurations.get(identifier)
        if not config:
            raise ValueError(f"No configuration registered for {identifier.identifier}")

        owner_class = cls._platform_class_mapping[identifier.platform]
        return cls.create_owner(owner_class, config)

    @classmethod
    def get_configuration(
        cls, identifier: OwnerIdentifier
    ) -> OwnerConfiguration | None:
        """Get a registered configuration for a platform and identifier.

        Args:
            platform: The platform to get the configuration for
            identifier: The owner identifier to get the configuration for

        Returns:
            The configuration if found, None otherwise
        """
        return cls._configurations.get(identifier)

    @classmethod
    def list_configurations(cls) -> dict[OwnerIdentifier, OwnerConfiguration]:
        """Get all registered configurations.

        Returns:
            A copy of the configurations dictionary
        """
        return cls._configurations.copy()

    @classmethod
    def create_owner(
        cls,
        owner_class: type[T],
        configuration: OwnerConfiguration,
    ) -> T:
        """Get or create an owner instance.

        This method implements the singleton pattern, ensuring that only one instance
        of an owner exists for a given class, platform and name combination.

        Args:
            owner_class: The class of the owner to create
            configuration: The owner configuration to use

        Returns:
            The owner instance
        """
        identifier = configuration.identifier
        if identifier in cls._cache:
            return cls._cache[identifier]  # type: ignore

        owner = owner_class(configuration=configuration)
        cls._cache[identifier] = owner
        return owner
