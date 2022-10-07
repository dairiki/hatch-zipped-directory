from hatchling.plugin.manager import PluginManager

from hatch_zipped_directory.builder import ZippedDirectoryBuilder


def test_hooks():
    plugin_manager = PluginManager()
    assert plugin_manager.builder.get("zipped-directory") is ZippedDirectoryBuilder
