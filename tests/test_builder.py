import hashlib
import json
import os
import re
from pathlib import Path
from zipfile import ZipFile

import pytest
from hatchling.builders.plugin.interface import IncludedFile
from hatchling.metadata.core import ProjectMetadata

from hatch_zipped_directory.builder import ZipArchive
from hatch_zipped_directory.builder import ZippedDirectoryBuilder

READ_SIZE = 65536


def getsha256(filename) -> str:
    sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        data = f.read(READ_SIZE)
        while data:
            sha256.update(data)
            data = f.read(READ_SIZE)
    return sha256.hexdigest()


def zip_contents(path):
    zf = ZipFile(path)
    files = {}
    for name in zf.namelist():
        with zf.open(name) as fp:
            files[name] = fp.read().decode("utf-8")
    return files


def zip_timestamps(path):
    zf = ZipFile(path)
    timestamps = []
    for info in zf.infolist():
        timestamps.append(info.date_time)
    return timestamps


def assert_zip_timestamps(archive_path, reproducible: bool):
    if reproducible:
        condition = lambda t: t == (2020, 2, 2, 0, 0, 0)
    else:
        condition = lambda t: t != (2020, 2, 2, 0, 0, 0)
    assert all(condition(t) for t in zip_timestamps(archive_path))


@pytest.mark.parametrize(
    "reproducible",
    [True, False],
    ids=lambda val: "[reproducible]" if val else "[non-reproducible]",
)
class TestZipArchive:
    def test_cleanup_on_error_in_init(self, tmp_path, monkeypatch, reproducible):
        monkeypatch.delattr("hatch_zipped_directory.builder.ZipFile")

        with pytest.raises(NameError):
            with ZipArchive.open(
                tmp_path / "test.zip", "install_name", reproducible=reproducible
            ):
                pass  # no cov
        assert len(list(tmp_path.iterdir())) == 0

    def test_cleanup_on_error(self, tmp_path, reproducible):
        archive_path = tmp_path / "test.zip"
        with pytest.raises(RuntimeError):
            with ZipArchive.open(
                archive_path, "install_name", reproducible=reproducible
            ):
                raise RuntimeError("test")
        assert len(list(tmp_path.iterdir())) == 0

    @pytest.mark.parametrize(
        "install_name, arcname_prefix",
        [
            ("install_prefix", "install_prefix/"),
            ("", ""),
            (".", ""),
        ],
    )
    def test_add_file(self, tmp_path, reproducible, install_name, arcname_prefix):
        relative_path = "src/foo"
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True)
        path.write_text("content")
        distribution_path = "bar"
        included_file = IncludedFile(
            os.fspath(tmp_path / relative_path), relative_path, distribution_path
        )

        archive_path = tmp_path / "test.zip"
        with ZipArchive.open(
            archive_path, install_name, reproducible=reproducible
        ) as archive:
            archive.add_file(included_file)

        assert zip_contents(archive_path) == {
            f"{arcname_prefix}bar": "content",
        }
        assert_zip_timestamps(archive_path, reproducible)

    @pytest.mark.parametrize(
        "install_name, arcname_prefix",
        [
            ("install_prefix", "install_prefix/"),
            ("", ""),
            (".", ""),
        ],
    )
    def test_write_file(self, tmp_path, reproducible, install_name, arcname_prefix):
        archive_path = tmp_path / "test.zip"
        with ZipArchive.open(
            archive_path, install_name, reproducible=reproducible
        ) as archive:
            archive.write_file("foo", "contents\n")

        assert zip_contents(archive_path) == {
            f"{arcname_prefix}foo": "contents\n",
        }
        assert_zip_timestamps(archive_path, reproducible)


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


@pytest.mark.parametrize("target_config", [{"core-metadata-version": "2.2"}])
def test_config_core_metadata_constructor(builder):
    metadata = builder.config.core_metadata_constructor(builder.metadata)
    assert re.search(r"(?im)^Metadata-Version: 2.2$", metadata)


@pytest.mark.parametrize("target_config", [{"core-metadata-version": None}])
def test_config_core_metadata_constructor_type_error(builder):
    with pytest.raises(TypeError, match="must be a string"):
        builder.config.core_metadata_constructor(builder.metadata)


@pytest.mark.parametrize("target_config", [{"core-metadata-version": "42.203"}])
def test_config_core_metadata_constructor_value_error(builder):
    with pytest.raises(ValueError, match="(?i)unknown metadata version"):
        builder.config.core_metadata_constructor(builder.metadata)


def test_ZippedDirectoryBuilder_clean(builder, tmp_path):
    dist_path = tmp_path / "dist"
    dist_path.mkdir()
    dist_path.joinpath("foo.whl").touch()
    dist_path.joinpath("bar.zip").touch()

    builder.clean(os.fspath(dist_path), ["standard"])

    assert list(dist_path.iterdir()) == [dist_path / "foo.whl"]


@pytest.mark.parametrize(
    "target_config, arcname_prefix",
    [
        ({}, "project_name/"),
        ({"install-name": "org.example.foo"}, "org.example.foo/"),
        ({"install-name": ""}, ""),
    ],
)
def test_ZippedDirectoryBuilder_build(builder, project_root, tmp_path, arcname_prefix):
    dist_path = tmp_path / "dist"
    project_root.joinpath("test.txt").write_text("content")

    artifacts = list(builder.build(os.fspath(dist_path)))

    assert len(artifacts) == 1
    artifact = Path(artifacts[0])
    assert artifact.relative_to(dist_path) == Path("project_name-1.23.zip")
    contents = zip_contents(artifact)
    assert set(contents) == {
        f"{arcname_prefix}test.txt",
        f"{arcname_prefix}METADATA.json",
    }
    assert_zip_timestamps(artifact, reproducible=True)
    json_metadata = json.loads(contents[f"{arcname_prefix}METADATA.json"])
    assert json_metadata["version"] == "1.23"


@pytest.mark.parametrize(
    "target_config",
    [
        {"reproducible": True},
        {"reproducible": False},
    ],
)
def test_ZippedDirectoryBuilder_reproducible(
    builder, project_root, tmp_path, target_config
):
    dist_path = tmp_path / "dist"
    test_file = project_root.joinpath("test.txt")
    test_file.write_text("content")

    digests = []
    for _ in range(0, 2):
        artifacts = list(builder.build(os.fspath(dist_path)))
        assert len(artifacts) == 1
        artifact = Path(artifacts[0])
        digests.append(getsha256(artifact))
        os.remove(artifact)
        # use some random epoch from the past, when `reproducible` enabled
        # then digest of archive should not change
        os.utime(test_file, (968250745, 968250745))
    if target_config["reproducible"]:
        assert digests[0] == digests[1]
    else:
        assert digests[0] != digests[1]


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
