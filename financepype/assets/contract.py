from enum import Enum
from typing import Any

from pydantic import field_validator

from financepype.assets.asset_id import AssetIdentifier
from financepype.assets.centralized_asset import CentralizedAsset
from financepype.markets.market import MarketInfo
from financepype.markets.trading_pair import TradingPair


class DerivativeSide(Enum):
    """Enumeration of possible derivative contract sides.

    Defines the possible positions that can be taken in a derivative contract:
    - LONG: Betting on price increase
    - SHORT: Betting on price decrease
    - BOTH: Represents both sides (typically used in market making)
    """

    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


class DerivativeContract(CentralizedAsset):
    """Represents a derivative contract asset.

    This class models financial derivative contracts such as futures or options.
    It extends the base Asset class with derivative-specific functionality and
    validation.

    Attributes:
        side (DerivativeSide): The side of the derivative contract (LONG/SHORT)
    """

    side: DerivativeSide

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation.

        Performs additional validation after the model is initialized.

        Args:
            __context (Any): The initialization context
        """
        super().model_post_init(__context)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: AssetIdentifier) -> AssetIdentifier:
        """Validate that the identifier represents a derivative instrument.

        Args:
            v (AssetIdentifier): The identifier to validate

        Returns:
            AssetIdentifier: The validated identifier

        Raises:
            ValueError: If the instrument is not a derivative type
        """
        trading_pair = TradingPair(name=v.value)
        if not trading_pair.market_info.is_derivative:
            raise ValueError("Instrument must be a derivative type")
        return v

    @field_validator("side")
    def validate_side(cls, v: DerivativeSide) -> DerivativeSide:
        """Validate that the derivative side is either LONG or SHORT.

        Args:
            v (DerivativeSide): The side to validate

        Returns:
            DerivativeSide: The validated side

        Raises:
            ValueError: If the side is not LONG or SHORT
        """
        if v not in [DerivativeSide.LONG, DerivativeSide.SHORT]:
            raise ValueError("Side must be either LONG or SHORT")
        return v

    @property
    def trading_pair(self) -> TradingPair:
        """Get the trading pair associated with this contract.

        Returns:
            TradingPair: The trading pair object
        """
        return TradingPair(name=self.symbol)

    @property
    def market_info(self) -> MarketInfo:
        """Get market information for this contract.

        Returns:
            MarketInfo: Market information including instrument type and details
        """
        return self.trading_pair.market_info
