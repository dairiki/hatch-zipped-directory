from hatchling.plugin.manager import PluginManager

from hatch_inkscape_extension.builder import InkscapeExtensionBuilder


def test_hooks():
    plugin_manager = PluginManager()
    assert plugin_manager.builder.get("inkscape-extension") is InkscapeExtensionBuilder
