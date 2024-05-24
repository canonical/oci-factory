import yaml


def string_constructor(loader, node):
    """change node type to string"""
    return loader.construct_scalar(node)


yaml.add_constructor(
    "tag:yaml.org,2002:int", string_constructor, Loader=yaml.SafeLoader
)
yaml.add_constructor(
    "tag:yaml.org,2002:float", string_constructor, Loader=yaml.SafeLoader
)
