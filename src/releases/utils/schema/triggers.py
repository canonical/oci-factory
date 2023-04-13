import pydantic

from datetime import datetime
from typing import Dict, List, Optional


LATEST_SCHEMA_VERSION = 1
KNOWN_RISKS_ORDERED = ["stable", "candidate", "beta", "edge"]


class ReleaseTriggerValidationError(Exception):
    """Error validating releases.yaml."""


class ChannelsSchema(pydantic.BaseModel):
    """Schema of the Channels within the releases.yaml file."""

    end_of_life: datetime = pydantic.Field(alias="end-of-life", default=None)
    stable: Optional[str]
    candidate: Optional[str]
    beta: Optional[str]
    edge: Optional[str]

    class Config:
        extra = pydantic.Extra.forbid

    @pydantic.validator("stable", "candidate", "beta", "edge", pre=True)
    def _check_risks(cls, values: List) -> str:
        """There must be at least one risk specified."""
        error = "At least one risk must be specified per track."
        if not any(values):
            raise ReleaseTriggerValidationError(error)

        return values


class ReleasesSchema(pydantic.BaseModel):
    """Validates the schema of the releases.yaml file."""

    version: str
    channels: Dict[str, ChannelsSchema]

    class Config:
        extra = pydantic.Extra.forbid
