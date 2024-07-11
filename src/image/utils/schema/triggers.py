import logging
import pydantic

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

LATEST_SCHEMA_VERSION = 1
KNOWN_RISKS_ORDERED = ["stable", "candidate", "beta", "edge"]


class ImageTriggerValidationError(Exception):
    """Error validating image trigger file."""


class ImageReachedEol(Exception):
    """Exception to be thrown when end-of-life is reached."""


class ImageUploadReleaseSchema(pydantic.BaseModel):
    """Schema of the release option for uploads in the image.yaml trigger"""

    end_of_life: datetime = pydantic.Field(alias="end-of-life")
    risks: List[Literal["edge", "beta", "candidate", "stable"]]

    class Config:
        extra = pydantic.Extra.allow

    @pydantic.root_validator(pre=True)
    def add_deprecated_field(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        """Determine if the track is deprecated based on end-of-life."""
        end_of_life = datetime.fromisoformat(values["end-of-life"])
        if end_of_life < datetime.now(timezone.utc):
            logging.warning("This track has reached its end of life")
            values["deprecated"] = True
        else:
            values["deprecated"] = False
        return values


class ImageUploadSchema(pydantic.BaseModel):
    """Schema of each upload within the image.yaml files."""

    source: str
    commit: str
    directory: str
    release: Optional[Dict[str, ImageUploadReleaseSchema]]

    class Config:
        extra = pydantic.Extra.allow


class ChannelsSchema(pydantic.BaseModel):
    """Schema of the 'release' tracks within the image.yaml file."""

    end_of_life: datetime = pydantic.Field(alias="end-of-life")
    stable: Optional[str]
    candidate: Optional[str]
    beta: Optional[str]
    edge: Optional[str]

    class Config:
        extra = pydantic.Extra.allow

    @pydantic.validator("stable", "candidate", "beta", "edge", pre=True)
    def _check_risks(cls, values: List) -> str:
        """There must be at least one risk specified."""
        error = "At least one risk must be specified per track."
        if not any(values):
            raise ImageTriggerValidationError(error)

        return values

    @pydantic.root_validator(pre=True)
    def add_deprecated_field(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        """Determine if the track is deprecated based on end-of-life."""
        end_of_life = datetime.fromisoformat(values["end-of-life"])
        if end_of_life < datetime.now(timezone.utc):
            logging.warning("This track has reached its end of life")
            values["deprecated"] = True
        else:
            values["deprecated"] = False
        return values


class ImageSchema(pydantic.BaseModel):
    """Validates the schema of the image.yaml files."""

    version: str
    upload: Optional[List[ImageUploadSchema]]
    release: Optional[Dict[str, ChannelsSchema]]

    class Config:
        extra = pydantic.Extra.allow
