from pathlib import Path

def is_symlink_dir(path):
    """Returns true if path is a symlink to a directory"""
    path_obj = Path(path)
    result = path_obj.is_dir() and path_obj.is_symlink()
    
    return result

def pytest_ignore_collect(path, config):
    """Since we use symlinks to ease imports from shared dir
    we need to skip symlinked paths from testing. Paths that
    return true in this function will be skipped."""

    skip_path = is_symlink_dir(path)
    return skip_path 