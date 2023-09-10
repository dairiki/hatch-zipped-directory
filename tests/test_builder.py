import json
import os
import re
import stat
import time
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


@pytest.fixture(
    params=[
        pytest.param(True, id="[reproducible]"),
        pytest.param(True, id="[non-reproducible]"),
    ]
)
def reproducible(request: pytest.FixtureRequest) -> bool:
    return request.param


def test_ZipArchive_cleanup_on_error_in_init(tmp_path, monkeypatch, reproducible):
    monkeypatch.delattr("hatch_zipped_directory.builder.ZipFile")

    with pytest.raises(NameError):
        with ZipArchive.open(
            tmp_path / "test.zip", "install_name", reproducible=reproducible
        ):
            pass  # no cov
    assert len(list(tmp_path.iterdir())) == 0


def test_ZipArchive_cleanup_on_error(tmp_path, reproducible):
    archive_path = tmp_path / "test.zip"
    with pytest.raises(RuntimeError):
        with ZipArchive.open(archive_path, "install_name", reproducible=reproducible):
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
def test_ZipArchive_add_file(tmp_path, reproducible, install_name, arcname_prefix):
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


@pytest.mark.parametrize(
    "install_name, arcname_prefix",
    [
        ("install_prefix", "install_prefix/"),
        ("", ""),
        (".", ""),
    ],
)
def test_ZipArchive_write_file(tmp_path, reproducible, install_name, arcname_prefix):
    archive_path = tmp_path / "test.zip"
    with ZipArchive.open(
        archive_path, install_name, reproducible=reproducible
    ) as archive:
        archive.write_file("foo", "contents\n")

    assert zip_contents(archive_path) == {
        f"{arcname_prefix}foo": "contents\n",
    }


def test_ZipArchive_reproducible_timestamps(tmp_path: Path) -> None:
    archive_path = tmp_path / "test.zip"
    src_path = tmp_path / "bar"
    src_path.touch()

    with ZipArchive.open(archive_path, root_path="", reproducible=True) as archive:
        archive.write_file("foo", "contents\n")
        archive.add_file(IncludedFile(os.fspath(src_path), "bar", "bar"))

    with ZipFile(archive_path) as zf:
        infolist = zf.infolist()
    assert len(infolist) == 2
    reproducible_ts = (2020, 2, 2, 0, 0, 0)
    assert all(info.date_time == reproducible_ts for info in infolist)


def test_ZipArchive_copies_timestamps_if_not_reproducible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = int(time.time() // 2) * 2  # NB: Zip timestamps have 2-second resolution
    now_date_tuple = time.localtime(now)[:6]
    monkeypatch.setattr("time.time", lambda: float(now))

    archive_path = tmp_path / "test.zip"
    src_path = tmp_path / "bar"
    src_path.touch()
    os.utime(src_path, (now, now))

    with ZipArchive.open(archive_path, root_path="", reproducible=False) as archive:
        archive.write_file("foo", "contents\n")
        archive.add_file(IncludedFile(os.fspath(src_path), "bar", "bar"))

    with ZipFile(archive_path) as zf:
        infolist = zf.infolist()
    assert len(infolist) == 2
    assert all(info.date_time == now_date_tuple for info in infolist)


@pytest.mark.parametrize(
    "original_mode, normalized_mode",
    [
        (0o400, 0o644),  # non-executable
        (0o500, 0o755),  # executable
    ],
    ids=oct,
)
def test_ZipArchive_file_modes(
    tmp_path: Path, reproducible: bool, original_mode: int, normalized_mode: int
) -> None:
    archive_path = tmp_path / "test.zip"
    src_path = tmp_path / "testfile"
    src_path.touch()
    src_path.chmod(original_mode)

    with ZipArchive.open(
        archive_path, root_path="", reproducible=reproducible
    ) as archive:
        archive.add_file(IncludedFile(os.fspath(src_path), "testfile", "testfile"))

    with ZipFile(archive_path) as zf:
        infolist = zf.infolist()
    assert len(infolist) == 1
    st_mode = infolist[0].external_attr >> 16
    assert stat.S_ISREG(st_mode)
    assert stat.S_IMODE(st_mode) == normalized_mode if reproducible else original_mode


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
    json_metadata = json.loads(contents[f"{arcname_prefix}METADATA.json"])
    assert json_metadata["version"] == "1.23"


@pytest.mark.parametrize("target_config", [{"reproducible": True}])
def test_ZippedDirectoryBuilder_reproducible(builder, project_root, tmp_path):
    dist_path = tmp_path / "dist"
    test_file = project_root.joinpath("test.txt")
    test_file.write_text("content")

    def build() -> Path:
        artifacts = list(builder.build(os.fspath(dist_path)))
        assert len(artifacts) == 1
        return Path(artifacts[0])

    zip1 = build()

    # use some random epoch from the past, when `reproducible` enabled
    # then digest of archive should not change
    os.utime(test_file, (968250745, 968250745))
    zip2 = build()

    assert zip1.read_bytes() == zip2.read_bytes()


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
