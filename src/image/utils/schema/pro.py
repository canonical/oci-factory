from typing import Literal

import pydantic
from pydantic import BaseModel, Field

# A Pro image can currently only be released by adding `upload[*].release` to the
# same build request. OCI Factory converts that request into internal
# `pro-release` data and publishes the resulting image only to
# `${ACR_REGISTRY}/<image-name>`. Pro releases are not uploaded to GHCR, Docker
# Hub, or public ECR, and do not create GitHub Releases or registry documentation
# updates. Maintainers cannot use `pro-release` directly to promote an existing
# Pro revision.

# Pro channels use the same risks, EOL handling, aliases, and risk backfilling as
# public channels. Services other than ESM are sorted and inserted between the
# application version and Ubuntu base. For example, `1.2-22.04` with `fips` and
# `ros` becomes `1.2-fips-ros-22.04`. `esm-apps` and `esm-infra` are omitted from
# the track name, so an ESM-only build retains `1.2-22.04`. A Pro track cannot be
# reused with a different full service combination.


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
