from collections.abc import Callable
from typing import Any

from financepype.assets.asset import Asset
from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.contract import DerivativeContract, DerivativeSide
from financepype.assets.spot import SpotAsset
from financepype.markets.market import InstrumentType, MarketInfo
from financepype.platforms.platform import Platform


class AssetFactory:
    """Factory class for creating and caching asset instances.

    This class provides a centralized way to create and manage asset instances.
    It uses a global cache to ensure that the same asset (identified by platform, symbol, and side)
    always returns the same instance, which is crucial for asset comparison and memory efficiency.

    The cache is global across all modules to ensure consistency, but provides methods
    for proper management and testing scenarios.
    """

    _cache: dict[tuple[str, str, Any], Asset] = {}
    _creators: dict[InstrumentType, Callable[[Platform, str, Any], Asset]] = {}

    @classmethod
    def reset(cls) -> None:
        """Reset the factory to its initial state.

        This method:
        1. Clears the asset cache
        2. Clears registered creators
        3. Re-registers default creators

        Useful for testing or when a complete reset is needed.
        """
        cls._cache.clear()
        cls._creators.clear()
        cls.register_default_creators()

    @classmethod
    def clear_cache(cls) -> None:
        """Clear only the asset cache, keeping creator registrations intact."""
        cls._cache.clear()

    @classmethod
    def get_cache_info(cls) -> dict[str, int]:
        """Get information about the current cache state.

        Returns:
            dict with cache statistics including:
            - cache_size: Number of cached assets
            - registered_creators: Number of registered creator functions
        """
        return {
            "cache_size": len(cls._cache),
            "registered_creators": len(cls._creators),
        }

    @classmethod
    def get_cached_assets(cls) -> list[tuple[str, str, Any]]:
        """Get a list of currently cached asset identifiers.

        Returns:
            List of tuples containing (platform_id, symbol, side) for each cached asset.
        """
        return list(cls._cache.keys())

    @classmethod
    def register_creator(
        cls,
        instrument_type: InstrumentType,
        creator: Callable[[Platform, str, Any], Asset],
    ) -> None:
        """Register a creator function for an instrument type."""
        cls._creators[instrument_type] = creator

    @classmethod
    def get_asset(cls, platform: Platform, symbol: str, **kwargs: Any) -> Asset:
        """Get or create an asset instance."""
        side = kwargs.get("side")
        cache_key = (platform.identifier, symbol, side)
        cached_asset = cls._cache.get(cache_key)
        if cached_asset is not None:
            return cached_asset

        market_info = None
        try:
            market_info = MarketInfo.split_client_instrument_name(symbol)
        except Exception:
            pass

        if market_info is not None and market_info.instrument_type in cls._creators:
            creator = cls._creators[market_info.instrument_type]
            asset = creator(platform, symbol, kwargs)
        else:
            asset = SpotAsset(
                platform=platform, identifier=AssetIdentifier(value=symbol)
            )

        cls._cache[cache_key] = asset
        return asset

    @classmethod
    def register_default_creators(cls) -> None:
        """Register the default creator functions for standard instrument types."""
        for instrument_type in InstrumentType:
            if instrument_type.is_spot:
                cls.register_creator(instrument_type, cls.create_spot)
            elif instrument_type.is_derivative:
                cls.register_creator(instrument_type, cls.create_derivative)

    @classmethod
    def create_derivative(
        cls, platform: Platform, symbol: str, kwargs: dict[str, Any]
    ) -> Asset:
        """Create a derivative contract asset.

        Args:
            platform (Platform): The trading platform
            symbol (str): The derivative contract symbol
            kwargs (dict[str, Any]): Additional arguments, including 'side' for the contract

        Returns:
            Asset: A new derivative contract instance
        """
        side = kwargs.get("side", DerivativeSide.BOTH)
        return DerivativeContract(
            platform=platform,
            identifier=AssetIdentifier(value=symbol),
            side=side,
        )

    @classmethod
    def create_spot(cls, platform: Platform, symbol: str, _: Any) -> Asset:
        """Create a spot trading asset.

        Args:
            platform (Platform): The trading platform
            symbol (str): The spot asset symbol
            _ (Any): Unused additional arguments

        Returns:
            Asset: A new spot asset instance
        """
        return SpotAsset(platform=platform, identifier=AssetIdentifier(value=symbol))


# Register default creators
AssetFactory.register_default_creators()
