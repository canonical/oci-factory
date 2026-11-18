def _get_platform_archs(rockcraft: dict, key: str) -> set[str]:
    archs = set()
    for platform, values in rockcraft["platforms"].items():
        platform_archs = (
            values.get(key, platform) if isinstance(values, dict) else platform
        )
        if isinstance(platform_archs, str):
            archs.add(platform_archs)
        elif isinstance(platform_archs, list):
            archs.update(platform_archs)
    return archs


def get_builder_archs(rockcraft: dict) -> set[str]:
    """Return the recipe's builder architectures."""
    return _get_platform_archs(rockcraft, "build-on")


def get_target_archs(rockcraft: dict) -> set[str]:
    """Return the recipe's target architectures."""
    return _get_platform_archs(rockcraft, "build-for")
