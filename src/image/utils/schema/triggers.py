import pydantic

from datetime import datetime
from typing import Dict, List, Literal, Optional


LATEST_SCHEMA_VERSION = 1
KNOWN_RISKS_ORDERED = ["stable", "candidate", "beta", "edge"]


class ImageTriggerValidationError(Exception):
    """Error validating image trigger file."""


class ImageUploadDockerfileSchema(pydantic.BaseModel):
    """Schema of the optional dockerfile-build section."""

    version: str
    platforms: List[str]

    class Config:
        extra = pydantic.Extra.forbid


class ImageUploadReleaseSchema(pydantic.BaseModel):
    """Schema of the release option for uploads in the image.yaml trigger"""

    end_of_life: Optional[datetime] = pydantic.Field(alias="end-of-life", default=None)
    risks: List[Literal["edge", "beta", "candidate", "stable"]]


class ImageUploadSchema(pydantic.BaseModel):
    """Schema of each upload within the image.yaml files."""

    source: str
    commit: str
    directory: str
    dockerfile_build: Optional[ImageUploadDockerfileSchema] = pydantic.Field(
        alias="dockerfile-build"
    )
    release: Optional[Dict[str, ImageUploadReleaseSchema]]

    class Config:
        extra = pydantic.Extra.forbid


class ChannelsSchema(pydantic.BaseModel):
    """Schema of the Channels within the releases.yaml file."""

    end_of_life: Optional[datetime] = pydantic.Field(alias="end-of-life", default=None)
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
            raise ImageTriggerValidationError(error)

        return values


class ImageSchema(pydantic.BaseModel):
    """Validates the schema of the image.yaml files."""

    version: str
    upload: Optional[List[ImageUploadSchema]]
    release: Optional[Dict[str, ChannelsSchema]]

    class Config:
        extra = pydantic.Extra.forbid
