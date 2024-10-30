from .triggers import ImageUploadSchema


class RevisionDataSchema(ImageUploadSchema):
    """Validates the schema of a revision data file."""

    name: str
    path: str
    revision: int
