from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "scoring_config.yaml"

GroupName = Literal["return_volume", "return_reasons", "item_mismatch", "return_timing", "behaviour"]


class _Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    points: int = Field(ge=0, le=100)


class HighReturnRatio(_Rule):
    threshold: float = Field(gt=0, lt=1)
    min_orders: int = Field(ge=1)


class HighReturnFrequency(_Rule):
    min_returns_90d: int = Field(ge=1)


class VagueReasons(_Rule):
    min_count: int = Field(ge=1)


class RepeatedReason(_Rule):
    min_share: float = Field(gt=0, le=1)
    min_returns: int = Field(ge=2)


class MismatchHistory(_Rule):
    multi_points: int = Field(ge=0, le=100)
    multi_threshold: int = Field(ge=2)


class ShortReturnWindow(_Rule):
    max_avg_days: float = Field(gt=0)
    min_returns: int = Field(ge=1)


class HighReturnCategories(_Rule):
    min_share: float = Field(gt=0, le=1)
    min_returns: int = Field(ge=1)


class ReturnsAfterHighRating(_Rule):
    min_rating: int = Field(ge=1, le=5)
    min_count: int = Field(ge=1)


class RisingReturnRate(_Rule):
    min_trend: float = Field(gt=1)
    min_recent_returns: int = Field(ge=1)


class Rules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    high_return_ratio: HighReturnRatio
    very_high_return_ratio: HighReturnRatio
    high_return_frequency: HighReturnFrequency
    vague_reasons: VagueReasons
    repeated_reason: RepeatedReason
    mismatch_history: MismatchHistory
    short_return_window: ShortReturnWindow
    high_return_categories: HighReturnCategories
    returns_after_high_rating: ReturnsAfterHighRating
    rising_return_rate: RisingReturnRate


class Levels(BaseModel):
    low_max: int = Field(ge=0, le=99)
    medium_max: int = Field(ge=1, le=99)

    @model_validator(mode="after")
    def _ordered(self) -> "Levels":
        if self.low_max >= self.medium_max:
            raise ValueError("levels.low_max must be lower than levels.medium_max")
        return self


class GroupCaps(BaseModel):
    model_config = ConfigDict(extra="forbid")
    return_volume: int = Field(ge=0, le=100)
    return_reasons: int = Field(ge=0, le=100)
    item_mismatch: int = Field(ge=0, le=100)
    return_timing: int = Field(ge=0, le=100)
    behaviour: int = Field(ge=0, le=100)


class ScoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=40)
    levels: Levels
    vague_reason_codes: list[str]
    vague_text_min_length: int = Field(ge=0)
    high_return_category_margin: float = Field(ge=0, le=1)
    group_caps: GroupCaps
    rules: Rules


def load_config_file(path: Path = DEFAULT_CONFIG_PATH) -> ScoringConfig:
    with path.open(encoding="utf-8") as handle:
        return ScoringConfig.model_validate(yaml.safe_load(handle))


def load_default_config() -> ScoringConfig:
    return load_config_file(DEFAULT_CONFIG_PATH)
