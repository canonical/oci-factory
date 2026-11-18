def get_builder_archs(rockcraft: dict) -> set[str]:
    """get list of builder architectures from rockcraft project definition"""

    rock_platforms = rockcraft["platforms"]

    target_archs = set()

    for platf, values in rock_platforms.items():

        if isinstance(values, dict) and "build-on" in values:
            if isinstance(arches := values["build-on"], list):
                target_archs.update(arches)
            elif isinstance(arches, str):
                target_archs.add(arches)
        else:
            target_archs.add(platf)

    return target_archs


def get_target_archs(rockcraft: dict) -> set[str]:
    """get list of target architectures from rockcraft project definition"""

    rock_platforms = rockcraft["platforms"]

    target_archs = set()

    for platf, values in rock_platforms.items():

        if isinstance(values, dict) and "build-for" in values:
            if isinstance(arches := values["build-for"], list):
                target_archs.update(arches)
            elif isinstance(arches, str):
                target_archs.add(arches)
        else:
            target_archs.add(platf)

    return target_archs
