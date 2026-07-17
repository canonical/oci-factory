# This file tracks the actions/read-ci-config/src/pro.py
# at https://github.com/canonical/rocks-template-actions/blob/a7bb0ec1ecd9bfdadbcd59e4a38911d6e7c4c32f/actions/read-ci-config/src/pro.py.

from typing import Literal, Optional
import pydantic
from pydantic import BaseModel, Field

UbuntuProServiceLiteral = Literal[
    "esm-apps",
    "esm-infra",
    "fips-updates",
    "fips",
    "fips-preview",
    "ros",
    "ros-updates",
]


class ProConfig(BaseModel):
    token: str = Field(
        ...,
        description="Ubuntu Pro token to use for building the rock",
    )
    artifact_passphrase: str = Field(
        ...,
        description="Passphrase to use for encrypting the Ubuntu Pro artifact",
        alias="artifact-passphrase",
    )

    model_config = pydantic.ConfigDict(extra="forbid", populate_by_name=True)

    @pydantic.field_validator("token", "artifact_passphrase")
    def _ensure_secret_format(cls, v):  # pylint: disable=no-self-argument
        if not v or not isinstance(v, str):
            raise ValueError("Credential name must be a non-empty string.")
        if not v.startswith("secrets."):
            raise ValueError("Credential name must start with 'secrets.'")
        return v


class Pro(BaseModel):
    services: list[UbuntuProServiceLiteral] = Field(
        ...,
        description="List of Ubuntu Pro services to build the rock with",
    )
    config: ProConfig = Field(
        ...,
        description="Configuration for building the rock with Ubuntu Pro",
    )

    model_config = pydantic.ConfigDict(extra="forbid")

    @pydantic.field_validator("services", mode="before")
    def _check_services(cls, v):
        invalid_services = [
            service for service in v if service not in UbuntuProServiceLiteral.__args__
        ]
        if invalid_services:
            raise ValueError(f"Invalid Ubuntu Pro service '{invalid_services[0]}'")
        return v
