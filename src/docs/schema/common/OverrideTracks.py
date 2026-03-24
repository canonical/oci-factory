from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime


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
