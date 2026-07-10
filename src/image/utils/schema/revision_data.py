from .triggers import ImageUploadSchema, ProSchema


class RevisionDataSchema(ImageUploadSchema):
    """Validates the schema of a revision data file."""

    name: str
    path: str
    revision: int
    track: str
    pro: ProSchema | None = None
