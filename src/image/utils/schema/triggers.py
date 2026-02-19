import pydantic

from datetime import datetime
from typing import Dict, List, Literal, Optional, Any


LATEST_SCHEMA_VERSION = 2
KNOWN_RISKS_ORDERED = ["stable", "candidate", "beta", "edge"]


class ImageTriggerValidationError(Exception):
    """Error validating image trigger file."""


class ImageReachedEol(Exception):
    """Exception to be thrown when end-of-life is reached."""


class ImageUploadReleaseSchema(pydantic.BaseModel):
    """Schema of the release option for uploads in the image.yaml trigger"""

    end_of_life: datetime = pydantic.Field(alias="end-of-life")
    # Unpack operator in subscript requires Python 3.11 or newer
    # TODO: when upgrading to 24.04, switch to the following line
    # risks: List[Literal[*KNOWN_RISKS_ORDERED]]
    risks: List[Literal["stable", "candidate", "beta", "edge"]]

    model_config = pydantic.ConfigDict(extra="forbid")

    @pydantic.field_validator("risks", mode="after")
    def _ensure_non_empty_risks(cls, value):
        if not value:
            raise ImageTriggerValidationError(
                "At least one upload risk must be present."
            )
        return value


class ImageUploadSchema(pydantic.BaseModel):
    """Schema of each upload within the image.yaml files."""

    source: str
    commit: str
    directory: str
    ignored_vulnerabilities: Optional[list[str]] = pydantic.Field(
        default_factory=list, alias="ignored-vulnerabilities"
    )
    release: Optional[Dict[str, ImageUploadReleaseSchema]] = None

    model_config = pydantic.ConfigDict(extra="forbid")


class ChannelsSchema(pydantic.BaseModel):
    """Schema of the 'release' tracks within the image.yaml file."""

    end_of_life: datetime = pydantic.Field(alias="end-of-life")
    stable: str = None
    candidate: str = None
    beta: str = None
    edge: str = None

    model_config = pydantic.ConfigDict(extra="forbid")

    @pydantic.model_validator(mode="after")
    def _check_risks(self, values: List) -> List:
        """There must be at least one risk specified."""
        error = "At least one risk must be specified per track."
        if not any([self.stable, self.candidate, self.beta, self.edge]):
            raise ImageTriggerValidationError(error)

        return values


class ImageSchema(pydantic.BaseModel):
    """Validates the schema of the image.yaml files."""

    version: str
    upload: Optional[List[ImageUploadSchema]] = None
    release: Optional[Dict[str, ChannelsSchema]] = None

    model_config = pydantic.ConfigDict(extra="forbid")

    @pydantic.field_validator("version", mode="before")
    def _ensure_version_is_str(cls, value: Any):
        """Ensure that version is always cast to str."""
        return str(value)

    @pydantic.field_validator("upload")
    def _ensure_unique_triggers(
        cls, v: Optional[List[ImageUploadSchema]]
    ) -> Optional[List[ImageUploadSchema]]:
        """Ensure that the triggers are unique."""
        if not v:
            return v
        unique_triggers = set()
        for upload in v:
            trigger = f"{upload.source}_{upload.commit}_{upload.directory}"
            if trigger in unique_triggers:
                raise ImageTriggerValidationError(
                    f"Image trigger {trigger} is not unique."
                )
            unique_triggers.add(trigger)
        return v

    @pydantic.field_validator("version")
    def _ensure_valid_version_number(cls, value: int) -> int:
        """Check that the schema version is supported."""
        error = (
            f"image.yaml schema version {value} is not supported. "
            f"Supported version is {','.join([str(i) for i in range(1, LATEST_SCHEMA_VERSION+1)])}."
        )
        if int(value) > LATEST_SCHEMA_VERSION:
            raise ImageTriggerValidationError(error)

        return value

    @pydantic.model_validator(mode="after")
    def _ensure_ignored_vuln_only_in_v2_and_later(
        cls, data: "ImageSchema"
    ) -> "ImageSchema":
        if data.version and int(data.version) < 2:
            if data.upload:
                for upload in data.upload:
                    if upload.ignored_vulnerabilities:
                        raise ImageTriggerValidationError(
                            '"ignored-vulnerabilities" field is not supported in '
                            f"image.yaml schema version {data.version}."
                        )
        return data
