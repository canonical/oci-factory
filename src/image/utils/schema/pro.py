from typing import Literal

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


def validate_pro_services(services: list[UbuntuProServiceLiteral]):
    """Validate constraints shared by Pro build and release service lists."""
    if not services:
        raise ValueError("At least one Ubuntu Pro service must be specified.")
    if len(services) != len(set(services)):
        raise ValueError("Ubuntu Pro services must be unique.")
    return services


class Pro(BaseModel):
    services: list[UbuntuProServiceLiteral] = Field(
        ...,
        description="List of Ubuntu Pro services to build the rock with",
    )
    model_config = pydantic.ConfigDict(extra="forbid")

    @pydantic.field_validator("services")
    def _check_services(cls, services):  # pylint: disable=no-self-argument
        return validate_pro_services(services)
