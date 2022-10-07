import json
import os
from pathlib import Path
from zipfile import ZipFile

import pytest
from hatchling.builders.plugin.interface import IncludedFile
from hatchling.metadata.core import ProjectMetadata

from hatch_zipped_directory.builder import ZipArchive
from hatch_zipped_directory.builder import ZippedDirectoryBuilder


def zip_contents(path):
    zf = ZipFile(path)
    files = {}
    for name in zf.namelist():
        with zf.open(name) as fp:
            files[name] = fp.read().decode("utf-8")
    return files


def test_ZipArchive_cleanup_on_error_in_init(tmp_path, monkeypatch):
    monkeypatch.delattr("hatch_zipped_directory.builder.ZipFile")

    with pytest.raises(NameError):
        with ZipArchive.open(tmp_path / "test.zip", "install_name"):
            pass  # no cov
    assert len(list(tmp_path.iterdir())) == 0


def test_ZipArchive_cleanup_on_error(tmp_path):
    archive_path = tmp_path / "test.zip"
    with pytest.raises(RuntimeError):
        with ZipArchive.open(archive_path, "install_name"):
            raise RuntimeError("test")
    assert len(list(tmp_path.iterdir())) == 0


def test_ZipArchive_add_file(tmp_path):
    relative_path = "src/foo"
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True)
    path.write_text("content")
    distribution_path = "bar"
    included_file = IncludedFile(
        os.fspath(tmp_path / relative_path), relative_path, distribution_path
    )

    archive_path = tmp_path / "test.zip"
    with ZipArchive.open(archive_path, "install_name") as archive:
        archive.add_file(included_file)

    assert zip_contents(archive_path) == {
        "install_name/bar": "content",
    }


def test_ZipArchive_write_file(tmp_path):
    archive_path = tmp_path / "test.zip"
    with ZipArchive.open(archive_path, "install_name") as archive:
        archive.write_file("foo", "contents\n")

    assert zip_contents(archive_path) == {
        "install_name/foo": "contents\n",
    }


@pytest.fixture
def project_root(tmp_path):
    root_path = tmp_path / "root"
    root_path.mkdir()
    return root_path


@pytest.fixture
def project_config():
    return {
        "name": "project-name",
        "version": "1.23",
    }


@pytest.fixture
def target_config():
    return {
        "install-name": "org.example.project",
    }


@pytest.fixture
def project_metadata(project_config, target_config, project_root):
    hatch_config = {
        "build": {
            "targets": {
                "zipped-directory": target_config,
            },
        },
    }
    config = {
        "project": project_config,
        "tool": {
            "hatch": hatch_config,
        },
    }
    return ProjectMetadata(project_root, None, config=config)


@pytest.fixture
def builder(project_root, project_metadata):
    return ZippedDirectoryBuilder(project_root, metadata=project_metadata)


def test_ZippedDirectoryBuilder_clean(builder, tmp_path):
    dist_path = tmp_path / "dist"
    dist_path.mkdir()
    dist_path.joinpath("foo.whl").touch()
    dist_path.joinpath("bar.zip").touch()

    builder.clean(os.fspath(dist_path), ["standard"])

    assert list(dist_path.iterdir()) == [dist_path / "foo.whl"]


def test_ZippedDirectoryBuilder_build(builder, project_root, tmp_path):
    dist_path = tmp_path / "dist"
    project_root.joinpath("test.txt").write_text("content")

    artifacts = list(builder.build(os.fspath(dist_path)))

    assert len(artifacts) == 1
    artifact = Path(artifacts[0])
    assert artifact.relative_to(dist_path) == Path("project_name-1.23.zip")
    contents = zip_contents(artifact)
    assert set(contents) == {
        "org.example.project/test.txt",
        "org.example.project/METADATA.json",
    }
    json_metadata = json.loads(contents["org.example.project/METADATA.json"])
    assert json_metadata["version"] == "1.23"


@pytest.mark.parametrize(
    "target_config, install_name",
    [
        ({"install-name": "org.example.foo"}, "org.example.foo"),
        ({}, "project_name"),
    ],
)
def test_ZippedDirectoryBuilder_build_data_install_name(builder, install_name):
    build_data = builder.get_default_build_data()
    assert build_data["install_name"] == install_name
    assert build_data["force_include"] == {}


@pytest.mark.parametrize(
    "project_config",
    [
        {"readme": "README.txt"},
    ],
)
def test_ZippedDirectoryBuilder_build_data_includes_readme(project_root, builder):
    project_root.joinpath("README.txt").touch()

    build_data = builder.get_default_build_data()

    assert build_data["force_include"] == {
        os.fspath(project_root / "README.txt"): "README.txt",
    }


def test_ZippedDirectoryBuilder_build_data_includes_license(project_root, builder):
    project_root.joinpath("COPYING").touch()

    build_data = builder.get_default_build_data()

    assert build_data["force_include"] == {
        os.fspath(project_root / "COPYING"): "COPYING",
    }
