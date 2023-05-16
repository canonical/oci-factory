import pydantic

from typing import Dict, Optional
from triggers import ImageUploadReleaseSchema


class PreReleaseSchema(pydantic.BaseModel):
    """Validates the schema of a pre-release."""

    release: Optional[Dict[str, ImageUploadReleaseSchema]]
    revision: str

    class Config:
        extra = pydantic.Extra.forbid
