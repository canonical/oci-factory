import argparse
from urllib.parse import urlparse
import re


def get_source_url(source: str) -> str:
    """Read a `source` string and normalize it to a format compatible with git clone.

    See `src.image.utils.schema.triggers` for definition of `source` string.
    """
    if urlparse(source).scheme in (  # match url with scheme
        "http",
        "https",
        "ssh",
        "git",
        "git+ssh",
    ):
        return source
    elif re.match(  # match and format GitHub <owner>/<repo>
        r"^[\w.-]+/[\w_.-]+$", source
    ):
        return f"https://github.com/{source}.git"
    else:
        raise ValueError(
            f"Invalid source format: {source}.\n Must be url to git repo or GitHub {{owner}}/{{repo}} format."
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        dest="input", type=str, help="The source string or URL to normalize."
    )
    args = parser.parse_args()

    normalized_url = get_source_url(args.input)
    print(normalized_url)


if __name__ == "__main__":
    main()
