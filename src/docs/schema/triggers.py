"""
this module is the pydantic version
of the documentation.yaml schema.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, conlist, constr, field_validator


class ConfigMapFile(BaseModel):
    """Schema of the microk8s[configmap][files] section."""

    key: str
    name: str
    link: str

    model_config = ConfigDict(extra="forbid")


class Microk8sConfigMap(BaseModel):
    """Schema of the microk8s[configmap] section."""

    name: Optional[str] = None
    files: conlist(item_type=ConfigMapFile, min_length=1)

    model_config = ConfigDict(extra="forbid")


class Microk8sDeploy(BaseModel):
    """Schema of the microk8s[deploy] section."""

    link: str
    access: str

    model_config = ConfigDict(extra="forbid")


class Microk8sInfo(BaseModel):
    """Schema of the microk8s section."""

    configmap: Optional[Microk8sConfigMap] = None
    deploy: Microk8sDeploy

    model_config = ConfigDict(extra="forbid")


class DockerRunParameters(BaseModel):
    """Schema of the docker section."""

    parameters: conlist(item_type=str, min_length=1)
    access: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class Parameter(BaseModel):
    """Schema of the parameters section."""

    type: str
    value: str
    description: str

    model_config = ConfigDict(extra="forbid")


class DebugInfo(BaseModel):
    """Schema of the debug section."""

    text: str

    model_config = ConfigDict(extra="forbid")


class EndOfLifeInfo(BaseModel):
    """Schema for end-of-life information."""

    end_of_life: str = Field(alias="end-of-life")

    model_config = ConfigDict(extra="forbid")

    @field_validator("end_of_life")
    def validate_end_of_life(cls, v: str) -> str:
        """Validate the end-of-life date format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(
                f"Invalid end-of-life date format: {v}. Expected ISO 8601 format."
            )
        return v


class DocSchema(BaseModel):
    """Schema of the documentation.yaml file, and also validation of the schema"""

    version: str
    application: constr(min_length=1, strip_whitespace=True)
    is_chiselled: Optional[bool] = None
    description: constr(min_length=1, strip_whitespace=True) = None
    docker: Optional[DockerRunParameters] = None
    parameters: Optional[conlist(item_type=Parameter, min_length=1)] = None
    debug: Optional[DebugInfo] = None
    microk8s: Optional[Microk8sInfo] = None
    override_tracks: Optional[dict[str, EndOfLifeInfo]] = None

    model_config = ConfigDict(extra="forbid")
