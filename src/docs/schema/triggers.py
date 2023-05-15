from typing import List, Optional
from pydantic import BaseModel, Extra, constr, conlist


class ConfigMapFile(BaseModel):
    """Schema of the microk8s[configmap][files] section."""

    key: str
    name: str
    link: str

    class Config:
        extra = Extra.forbid


class Microk8sConfigMap(BaseModel):
    """Schema of the microk8s[configmap] section."""

    name: Optional[str]
    files: conlist(item_type=List[ConfigMapFile], min_items=1) = None

    class Config:
        extra = Extra.forbid


class Microk8sDeploy(BaseModel):
    """Schema of the microk8s[deploy] section."""

    link: str
    access: str

    class Config:
        extra = Extra.forbid


class Microk8sInfo(BaseModel):
    """Schema of the microk8s section."""

    configmap: Optional[Microk8sConfigMap]
    deploy: Microk8sDeploy

    class Config:
        extra = Extra.forbid


class DockerRunParameters(BaseModel):
    """Schema of the docker section."""

    parameters: conlist(item_type=List[str], min_items=1)
    access: Optional[str]

    class Config:
        extra = Extra.forbid


class Parameter(BaseModel):
    """Schema of the parameters section."""

    type: str
    value: str
    description: Optional[str]

    class Config:
        extra = Extra.forbid


class DebugInfo(BaseModel):
    """Schema of the debug section."""

    text: str

    class Config:
        extra = Extra.forbid


class DocSchema(BaseModel):
    """Schema of the documentation.yaml file, and also validation of the schema"""

    version: int
    application: constr(min_length=1, strip_whitespace=True)
    is_chiselled: Optional[bool]
    description: constr(min_length=1, strip_whitespace=True)
    docker: Optional[DockerRunParameters]
    parameters: Optional[conlist(item_type=List[Parameter], min_items=1)]
    debug: Optional[DebugInfo]
    microk8s: Optional[Microk8sInfo]

    class Config:
        extra = Extra.forbid
