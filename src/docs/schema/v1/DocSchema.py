"""
this module is the pydantic version
of the documentation.yaml schema.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, conlist, constr, field_validator

from ..common.Microk8s import Microk8sInfo
from ..common.OverrideTracks import EndOfLifeInfo


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
