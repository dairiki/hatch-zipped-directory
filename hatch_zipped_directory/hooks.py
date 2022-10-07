from hatchling.plugin import hookimpl

from .builder import ZippedDirectoryBuilder


@hookimpl
def hatch_register_builder():
    return ZippedDirectoryBuilder
