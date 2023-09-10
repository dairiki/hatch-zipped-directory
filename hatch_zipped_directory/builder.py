from __future__ import annotations

import json
import os
import shutil
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Iterator
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile
from zipfile import ZipInfo

from hatchling.builders.config import BuilderConfig
from hatchling.builders.plugin.interface import BuilderInterface
from hatchling.builders.plugin.interface import IncludedFile
from hatchling.builders.utils import get_reproducible_timestamp
from hatchling.builders.utils import normalize_file_permissions
from hatchling.builders.utils import normalize_relative_path
from hatchling.builders.utils import set_zip_info_mode
from hatchling.metadata.spec import DEFAULT_METADATA_VERSION
from hatchling.metadata.spec import get_core_metadata_constructors

from .metadata import metadata_to_json
from .utils import atomic_write

if sys.version_info >= (3, 8):  # no cov
    from functools import cached_property as optionally_cached_property
else:  # no cov
    optionally_cached_property = property


__all__ = ["ZippedDirectoryBuilder"]


class ZipArchive:
    def __init__(self, zipfd: ZipFile, root_path: str, *, reproducible: bool = True):
        self.root_path = PurePosixPath(root_path)
        self.zipfd = zipfd
        self.reproducible = reproducible

    def add_file(self, included_file: IncludedFile) -> None:
        # Logic mostly copied from hatchling.builders.wheel.WheelArchive.add_file
        # https://github.com/pypa/hatch/blob/7dac9856d2545393f7dd96d31fc8620dde0dc12d/backend/src/hatchling/builders/wheel.py#L84-L112
        arcname = self.root_path / included_file.distribution_path
        zinfo = ZipInfo.from_file(included_file.path, arcname)
        if zinfo.is_dir():
            raise ValueError(  # no cov
                "ZipArchive.add_file does not support adding directories"
            )

        if self.reproducible:
            zinfo.date_time = self._reproducible_date_time
            # normalize mode (https://github.com/takluyver/flit/pull/66)
            st_mode = (zinfo.external_attr >> 16) & 0xFFFF
            set_zip_info_mode(zinfo, normalize_file_permissions(st_mode) & 0xFFFF)

        with open(included_file.path, "rb") as src, self.zipfd.open(zinfo, "w") as dest:
            shutil.copyfileobj(src, dest, 8 * 1024)  # type: ignore[misc] # mypy #14975

    def write_file(self, path: str, data: bytes | str) -> None:
        arcname = self.root_path / path
        if self.reproducible:
            date_time = self._reproducible_date_time
        else:
            date_time = time.localtime(time.time())[:6]
        self.zipfd.writestr(ZipInfo(os.fspath(arcname), date_time=date_time), data)

    @classmethod
    @contextmanager
    def open(
        cls, dst: str | os.PathLike[str], root_path: str, *, reproducible: bool = True
    ) -> Iterator[ZipArchive]:
        with atomic_write(dst) as fp:
            with ZipFile(fp, "w", compression=ZIP_DEFLATED) as zipfd:
                yield cls(zipfd, root_path, reproducible=reproducible)

    @optionally_cached_property
    def _reproducible_date_time(self):
        return time.gmtime(get_reproducible_timestamp())[0:6]


class ZippedDirectoryBuilderConfig(BuilderConfig):
    @property
    def core_metadata_constructor(self):
        core_metadata_version = self.target_config.get(
            "core-metadata-version", DEFAULT_METADATA_VERSION
        )
        if not isinstance(core_metadata_version, str):
            raise TypeError(
                f"Field `tool.hatch.build.targets.{self.plugin_name}."
                "core-metadata-version` must be a string"
            )
        constructors = get_core_metadata_constructors()
        if core_metadata_version not in constructors:
            raise ValueError(
                f"Unknown metadata version `{core_metadata_version}` for field "
                f"`tool.hatch.build.targets.{self.plugin_name}.core-metadata-version`. "
                f'Available: {", ".join(sorted(constructors))}'
            )
        return constructors[core_metadata_version]


class ZippedDirectoryBuilder(BuilderInterface):
    PLUGIN_NAME = "zipped-directory"

    @classmethod
    def get_config_class(cls):
        return ZippedDirectoryBuilderConfig

    def get_version_api(self) -> dict[str, Callable[..., str]]:
        return {"standard": self.build_standard}

    def clean(self, directory: str, versions: Iterable[str]) -> None:
        for filename in os.listdir(directory):
            if filename.endswith(".zip"):
                os.remove(os.path.join(directory, filename))

    def build_standard(self, directory: str, **build_data: Any) -> str:
        project_name = self.normalize_file_name_component(self.metadata.core.raw_name)
        target = Path(directory, f"{project_name}-{self.metadata.version}.zip")

        install_name: str = build_data["install_name"]

        with ZipArchive.open(
            target, install_name, reproducible=self.config.reproducible
        ) as archive:
            for included_file in self.recurse_included_files():
                archive.add_file(included_file)

            json_metadata = metadata_to_json(
                self.config.core_metadata_constructor(self.metadata)
            )
            archive.write_file("METADATA.json", json.dumps(json_metadata, indent=2))
        return os.fspath(target)

    def get_default_build_data(self) -> dict[str, Any]:
        build_data: dict[str, Any] = super().get_default_build_data()

        extra_files = []
        if self.metadata.core.readme_path:
            extra_files.append(self.metadata.core.readme_path)
        if self.metadata.core.license_files:
            extra_files.extend(self.metadata.core.license_files)

        force_include = build_data.setdefault("force_include", {})
        for fn in map(normalize_relative_path, extra_files):
            force_include[os.path.join(self.root, fn)] = Path(fn).name

        if "install-name" in self.target_config:
            install_name = self.target_config["install-name"]
        else:
            install_name = self.normalize_file_name_component(
                self.metadata.core.raw_name
            )
        build_data["install_name"] = install_name

        return build_data
