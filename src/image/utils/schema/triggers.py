import pydantic

from datetime import datetime
from typing import Dict, List, Literal, Optional, Any, get_args


LATEST_SCHEMA_VERSION = 1
KNOWN_RISKS_ORDERED_LITERAL = Literal["stable", "candidate", "beta", "edge"]
KNOWN_RISKS_ORDERED = list(get_args(KNOWN_RISKS_ORDERED_LITERAL))
KNOWN_PRO_SERVICES = Literal[
    "esm-apps",
    "esm-infra",
    "fips",
    "fips-preview",
    "fips-updates",
]


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
    risks: List[KNOWN_RISKS_ORDERED_LITERAL]

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

class ImageDeployRepoSchema(pydantic.BaseModel):

    registry: str
    namespace: str

    model_config = pydantic.ConfigDict(extra="forbid")


class ImageBuildDeploySchema(pydantic.BaseModel):

    repositories: List[ImageDeployRepoSchema]
    risks: List[KNOWN_RISKS_ORDERED_LITERAL]

class ImageBuildSchema(pydantic.BaseModel):

    directory: str
    tag: str
    pro: Optional[List[KNOWN_PRO_SERVICES]] = None
    deploy: Optional[ImageBuildDeploySchema] = None

    model_config = pydantic.ConfigDict(extra="forbid")


class ImageSchema(pydantic.BaseModel):
    """Validates the schema of the image.yaml files."""

    version: str
    upload: Optional[List[ImageUploadSchema]] = None
    release: Optional[Dict[str, ChannelsSchema]] = None
    build: Optional[List[ImageBuildSchema]] = None

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

    @pydantic.field_validator("build")
    def _ensure_unique_build_dirs(
        cls, v: Optional[List[ImageBuildSchema]]
    ) -> Optional[List[ImageBuildSchema]]:
        """Ensure that the build directories are unique."""
        if not v:
            return v
        unique_dirs = set()
        for build in v:
            dir = build.directory.strip("/")
            if dir in unique_dirs:
                raise ImageTriggerValidationError(
                    f"Build directory {dir} is not unique."
                )
            unique_dirs.add(dir)
        return v

    @pydantic.model_validator(mode="before")
    def _ensure_mutually_exclusive_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure that 'build' is mutually exclusive with 'upload' and 'release'."""
        if "build" in values and ("upload" in values or "release" in values):
            raise ImageTriggerValidationError(
                "'build' cannot be used with 'upload' or 'release'."
            )
        return values
