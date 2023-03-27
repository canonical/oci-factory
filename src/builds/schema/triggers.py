import pydantic

from typing import Dict, List, Literal, Optional


class BuildsImageDockerfileSchema(pydantic.BaseModel):
    """Schema of the optional dockerfile-build section."""

    version: str
    platforms: List[str]

    class Config:
        extra = pydantic.Extra.forbid


class BuildsImageSchema(pydantic.BaseModel):
    """Schema of the Images within the builds.yaml files."""

    source: str
    commit: str
    directory: str
    dockerfile_build: Optional[BuildsImageDockerfileSchema] = pydantic.Field(
        alias="dockerfile-build"
    )
    release_to: Optional[
        Dict[Literal["risks"], List[Literal["edge", "beta", "candidate", "stable"]]]
    ] = pydantic.Field(alias="release-to")

    class Config:
        extra = pydantic.Extra.forbid


class BuildsSchema(pydantic.BaseModel):
    """Validates the schema of the builds.yaml files"""

    version: str
    images: List[BuildsImageSchema]

    class Config:
        extra = pydantic.Extra.forbid
