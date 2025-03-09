from typing import TypeVar

from financepype.operators.operator import Operator, OperatorConfiguration
from financepype.platforms.platform import Platform

T = TypeVar("T", bound=Operator)


class OperatorFactory:
    """Factory class for creating and caching operator instances.

    This class provides a centralized way to create and manage operator instances.
    It uses a global cache to ensure that the same operator (identified by platform)
    always returns the same instance, which is crucial for maintaining state and memory efficiency.

    The primary way to use the factory is through platforms:
    1. Register operator classes for platforms
    2. Register configurations for platforms
    3. Get operators using platforms

    Example:
        >>> platform = Platform(identifier="binance")
        >>> OperatorFactory.register_operator_class(platform, ExchangeOperator)
        >>> config = OperatorConfiguration(platform=platform)
        >>> OperatorFactory.register_configuration(platform, config)
        >>> operator1 = OperatorFactory.get(platform)  # Type inferred from platform
        >>> operator2 = OperatorFactory.get(platform)
        >>> assert operator1 is operator2  # Same instance
    """

    _platform_class_mapping: dict[Platform, type[Operator]] = {}
    _configurations: dict[Platform, OperatorConfiguration] = {}
    _cache: dict[tuple[type[Operator], Platform], Operator] = {}

    @classmethod
    def reset(cls) -> None:
        """Reset the factory to its initial state.

        This method:
        1. Clears the operator cache
        2. Clears registered operator classes
        3. Clears registered configurations

        Useful for testing or when a complete reset is needed.
        """
        cls._cache.clear()
        cls._platform_class_mapping.clear()
        cls._configurations.clear()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear only the operator cache, keeping registrations intact."""
        cls._cache.clear()

    @classmethod
    def get_cache_info(cls) -> dict[str, int]:
        """Get information about the current cache state.

        Returns:
            dict with cache statistics including:
            - cache_size: Number of cached operators
            - registered_operator_classes: Number of registered operator classes
            - registered_configurations: Number of registered configurations
        """
        return {
            "cache_size": len(cls._cache),
            "registered_operator_classes": len(cls._platform_class_mapping),
            "registered_configurations": len(cls._configurations),
        }

    @classmethod
    def register_operator_class(
        cls, platform: Platform, operator_class: type[Operator]
    ) -> None:
        """Register an operator class for a platform.

        This associates a specific operator implementation with a platform.
        When creating operators, the factory will automatically use the correct class
        based on the platform.

        Args:
            platform: The platform to register for
            operator_class: The operator class to use for this platform

        Raises:
            ValueError: If a class is already registered for this platform
        """
        if platform in cls._platform_class_mapping:
            raise ValueError(
                f"Operator class already registered for platform '{platform}'"
            )
        cls._platform_class_mapping[platform] = operator_class

    @classmethod
    def register_configuration(cls, configuration: OperatorConfiguration) -> None:
        """Register a configuration.

        This is the primary way to register configurations in the factory.
        Each platform can have only one configuration at a time.

        Args:
            configuration: The operator configuration to register

        Raises:
            ValueError: If a configuration already exists for this platform
            ValueError: If no operator class is registered for the platform
        """
        platform = configuration.platform
        if platform in cls._configurations:
            raise ValueError(
                f"Configuration already registered for platform '{platform}'"
            )

        if platform not in cls._platform_class_mapping:
            raise ValueError(
                f"No operator class registered for platform '{platform}'. "
                "Register a class first using register_operator_class()"
            )

        cls._configurations[platform] = configuration

    @classmethod
    def get(cls, platform: Platform) -> Operator:
        """Get or create an operator instance for a platform.

        This is the primary way to get operator instances from the factory.
        The operator class and configuration are automatically determined from the platform.

        Args:
            platform: The platform to get an operator for

        Returns:
            The operator instance

        Raises:
            ValueError: If no configuration is registered for the platform
        """
        config = cls._configurations.get(platform)
        if not config:
            raise ValueError(f"No configuration registered for platform '{platform}'")

        operator_class = cls._platform_class_mapping[platform]
        return cls.create_operator(operator_class, config)

    @classmethod
    def get_configuration(cls, platform: Platform) -> OperatorConfiguration | None:
        """Get a registered configuration for a platform.

        Args:
            platform: The platform to get the configuration for

        Returns:
            The configuration if found, None otherwise
        """
        return cls._configurations.get(platform)

    @classmethod
    def list_configurations(cls) -> dict[Platform, OperatorConfiguration]:
        """Get all registered configurations.

        Returns:
            A copy of the configurations dictionary
        """
        return cls._configurations.copy()

    @classmethod
    def create_operator(
        cls,
        operator_class: type[T],
        configuration: OperatorConfiguration,
    ) -> T:
        """Get or create an operator instance.

        This method implements the singleton pattern, ensuring that only one instance
        of an operator exists for a given class and configuration.

        Args:
            operator_class: The class of the operator to create
            configuration: The operator configuration to register

        Returns:
            The operator instance
        """
        cache_key = (operator_class, configuration.platform)
        if cache_key in cls._cache:
            return cls._cache[cache_key]  # type: ignore

        operator = operator_class(configuration=configuration)
        cls._cache[cache_key] = operator
        return operator
