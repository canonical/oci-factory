from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Microk8sInfo(BaseModel):
    """Schema of the microk8s section."""

    configmap: Microk8sConfigMap | None = Field(
        default=None,
        description="Configmap(s) needed for deployment."
    )
    deploy: Microk8sDeploy = Field(
        ...,
        description="Link to the YAML manifest and additional access message."
    )

    model_config = ConfigDict(extra="forbid")


class Microk8sConfigMap(BaseModel):
    """Schema of the microk8s[configmap] section."""

    name: str | None = Field(
        default=None,
        description="Name of the configmap resource."
    )
    files: list[ConfigMapFile] = Field(
        ...,
        min_length=1,
        description="List of ConfigMap files."
    )

    model_config = ConfigDict(extra="forbid")


class ConfigMapFile(BaseModel):
    """Schema of the microk8s[configmap][files] section."""

    key: str = Field(..., description="Key name for the file.")
    name: str = Field(..., description="Name of the actual file.")
    link: str = Field(..., description="Link where to fetch the file from.")

    model_config = ConfigDict(extra="forbid")


class Microk8sDeploy(BaseModel):
    """Schema of the microk8s[deploy] section."""

    link: str = Field(..., description="Link to the raw manifest file.")
    access: str = Field(..., description="Post deployment access message.")

    model_config = ConfigDict(extra="forbid")
