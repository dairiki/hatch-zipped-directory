import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture(scope="session")
def plugin_uri(tmp_path_factory, pytestconfig):
    """Generate URI to a temporary copy of our source code.

    To ensure that ``hatch build`` is run with a current copy of our
    plugin, we need a unique URI per pytest session in order to defeat
    hatch's wheel cache.

    """
    project_path = Path(pytestconfig.rootdir)
    plugin_path = tmp_path_factory.mktemp("plugin")
    shutil.copytree(
        project_path,
        plugin_path,
        ignore=shutil.ignore_patterns(".git", "__pycache__"),
        dirs_exist_ok=True,
    )
    return plugin_path.resolve().as_uri()


PYPROJECT_TMPL = """
[build-system]
requires = [
    "hatchling",
    "hatch-zipped-directory @ {plugin_uri}",
]
build-backend = "hatchling.build"

[project]
name = "demo"
version = "0.42"
readme = "README.md"

[tool.hatch.build.targets.zipped-directory]
install-name = "org.example.test"
only-include = ["src"]
sources = ["src"]
"""


@pytest.fixture
def demo_path(tmp_path, plugin_uri):
    project_path = tmp_path / "demo-project"
    project_path.mkdir()

    project_file = project_path / "pyproject.toml"
    project_file.write_text(
        PYPROJECT_TMPL.format(plugin_uri=plugin_uri),
        encoding="utf-8",
    )

    for src in (
        "LICENSE.txt",
        "README.md",
        "src/code.py",
        "src/subdir/data.txt",
        "tests/ignored.txt",
    ):
        file_path = project_path / src
        file_path.parent.mkdir(exist_ok=True, parents=True)
        file_path.write_text("dummy", encoding="utf-8")

    return project_path


@pytest.fixture
def demo_zipfile_path(demo_path):
    subprocess.run(
        [sys.executable, "-m", "hatch", "build", "--target", "zipped-directory"],
        cwd=demo_path,
        env={
            **os.environ,
            "SETUPTOOLS_SCM_PRETEND_VERSION": "0.1a1",
            "HATCH_ENV_ACTIVE": "",
        },
        check=True,
    )
    return demo_path / "dist/demo-0.42.zip"


def test_build_demo(demo_zipfile_path):
    with ZipFile(demo_zipfile_path) as zf:
        assert set(zf.namelist()) == {
            # from src/
            "org.example.test/code.py",
            "org.example.test/subdir/data.txt",
            # core metadata files
            "org.example.test/LICENSE.txt",
            "org.example.test/METADATA.json",
            "org.example.test/README.md",
            # directory entries
            # (see https://github.com/dairiki/hatch-zipped-directory/pull/4)
            "org.example.test/",
            "org.example.test/subdir/",
        }


def test_demo_zipfile_hash(demo_zipfile_path):
    with open(demo_zipfile_path, "rb") as fp:
        zip_sha1 = hashlib.sha1(fp.read()).hexdigest()

    # FIXME: On windows hash appears to come out different.
    # I haven't yet determined why.
    if (  # pragma: no cover
        sys.platform == "win32"
        and zip_sha1 == "6f4c0a6c93d8c2beb7afe867258a74bdf631c162"
    ):
        pytest.xfail("hash differs on windows for undetermined reason")

    assert zip_sha1 == "d720257ddf13e89d068fafde0ea920990d1d37a2"
