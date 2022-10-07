from hatchling.plugin import hookimpl

from .builder import InkscapeExtensionBuilder


@hookimpl
def hatch_register_builder():
    return InkscapeExtensionBuilder
