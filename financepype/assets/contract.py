from enum import Enum
from typing import Any

from pydantic import field_validator

from financepype.assets.asset import Asset
from financepype.assets.asset_id import AssetIdentifier
from financepype.markets.market import MarketInfo
from financepype.markets.trading_pair import TradingPair


class DerivativeSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


class DerivativeContract(Asset):
    side: DerivativeSide

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: AssetIdentifier) -> AssetIdentifier:
        trading_pair = TradingPair(name=v.value)
        if not trading_pair.instrument_info.is_derivative:
            raise ValueError("Instrument must be a derivative type")
        return v

    @field_validator("side")
    def validate_side(cls, v: DerivativeSide) -> DerivativeSide:
        if v not in [DerivativeSide.LONG, DerivativeSide.SHORT]:
            raise ValueError("Side must be either LONG or SHORT")
        return v

    @property
    def trading_pair(self) -> TradingPair:
        return TradingPair(name=self.identifier.value)

    @property
    def instrument_info(self) -> MarketInfo:
        return self.trading_pair.instrument_info
