import pytest

from src.shared.source_url import get_source_url


@pytest.mark.parametrize(
    "schema",
    ["http", "https", "ssh", "git"],
)
def test_get_source_url_valid_schemas(schema):
    """Ensure valid URL schemas are returned w/o modification."""
    source = f"{schema}://example.com/repo.git"
    assert get_source_url(source) == source


def test_get_source_url_github_format():
    """Ensure GitHub formatted 'owner/repo' is converted to a valid URL."""
    assert get_source_url("owner/repo") == "https://github.com/owner/repo.git"


@pytest.mark.parametrize(
    "invalid_source",
    [
        "invalid_source",
        "://missing-schema.com",
        "invalid://schema.com",
        "owner/repo/extra",
        "",
    ],
)
def test_get_source_url_invalid_format(invalid_source):
    """Ensure invalid source formats raise a ValueError."""
    with pytest.raises(ValueError, match="Invalid source format: .*"):
        get_source_url(invalid_source)
