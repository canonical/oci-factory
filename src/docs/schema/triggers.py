"""
this module is the pydantic version
of the documentation.yaml schema.
"""

from typing import Optional
from pydantic import BaseModel, constr, conlist, ConfigDict


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

    model_config = ConfigDict(extra="forbid")
