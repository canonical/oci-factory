"""
this module is the pydantic version
of the documentation.yaml schema.
"""
from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator
from pydantic.networks import HttpUrl, AnyUrl

from ..common.Microk8s import Microk8sInfo
from ..common.OverrideTracks import EndOfLifeInfo

#
# Docker Run Fields
#
class DockerRunBase(BaseModel):
    """Base schema of the docker section."""

    parameters: str | None = Field(
        default=None,
        description="Additional docker run parameters for the example",
    )
    run_cmd: str | None = Field(
        default=None,
        alias="run-cmd",
        description="Example of a docker run command.",
    )
    run_conclusion: str | None = Field(
        default=None,
        alias="run-conclusion",
        description="A free-text example of what to expect after the docker run command.",
    )

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )


class DockerRun(DockerRunBase):
    """Schema of the docker section."""

    dockerfile: str | None = Field(
        default=None,
        description="Example of a full Dockerfile showing the rock being used as a base for other applications.",
    )

    legacy: DockerRunBase | None = Field(
        default=None,
        description="To be used when there are both Docker images and rocks in the same registry repository."
    )

    # Validate either dockerfile or parent.run_conclusion is provided
    @model_validator(mode="after")
    def check_dockerfile_or_run_conclusion(self):
        if not self.dockerfile and not self.run_conclusion:
            raise ValueError(
                "Either 'dockerfile' or 'run-conclusion' must be provided."
            )
        return self

    # Validate any of the fields in the legacy section if legacy is provided
    @model_validator(mode="after")
    def check_legacy_fields(self):
        if self.legacy:
            if not any([self.legacy.parameters, self.legacy.run_cmd, self.legacy.run_conclusion]):
                raise ValueError("At least one of 'parameters', 'run-cmd', or 'run-conclusion' must be provided in the 'legacy' section.")
        return self

#
# Config fields
#
class ConfigOption(BaseModel):
    """Schema of a config option."""

    default: str | None = Field(
        default=None,
        description="The default value of the configuration option, if applicable.",
    )
    description: str = Field(
        ...,
        description="A description of the configuration option.",
    )
    type: Literal["env", "mount", "port", "app", "other"] = Field(
        ...,
        description="The type of the configuration option.",
    )

    model_config = ConfigDict(extra="forbid")

#
# Main Schema
#
class DocSchema(BaseModel):
    """Schema of the documentation.yaml file, and also validation of the schema"""

    version: str = Field(..., description="Schema version, should be 2")
    application: str = Field(..., description="Human-readable name of the container image.", min_length=1, strip_whitespace=True)
    description: str = Field(..., description="Long image description.", min_length=1, strip_whitespace=True)
    website: HttpUrl = Field(..., description="The link to the original software's web pages.")
    issues: HttpUrl = Field(
        default="https://bugs.launchpad.net/ubuntu-docker-images",
        description="The link for submitting issues, bugs, and feature requests."
    )
    source_code: AnyUrl | None = Field(
        default=None,
        alias="source-code",
        description="The links to the source code of the rock or the original product."
    )
    docker: DockerRun = Field(
        ..., 
        description="Minimal docker run example for the image."
    )
    config: dict[str, ConfigOption] | None = Field(
        default=None,
        description="List of relevant runtime configurations for the rock ."
    )
    microk8s: Microk8sInfo | None = Field(
        default=None,
        description="Specific information for Kubernetes deployments."
    )
    override_tracks: dict[str, EndOfLifeInfo] | None = Field(
        default=None,
        alias="override-tracks",
        description="Override end-of-life tracks for the rock, if applicable."
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_serializer("website", "issues", "source_code")
    def serialize_url(self, url: AnyUrl) -> str:
        return str(url)
