from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Iterator
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from hatchling.builders.plugin.interface import BuilderInterface
from hatchling.builders.plugin.interface import IncludedFile
from hatchling.builders.utils import normalize_relative_path

from .metadata import json_metadata_2_1
from .utils import atomic_write

__all__ = ["ZippedDirectoryBuilder"]


class ZipArchive:
    def __init__(self, zipfd: ZipFile, root_path: str):
        self.root_path = root_path
        self.zipfd = zipfd

    def add_file(self, included_file: IncludedFile) -> None:
        arcname = f"{self.root_path}/{included_file.distribution_path}"
        self.zipfd.write(included_file.path, arcname=arcname)

    def write_file(self, path: str, data: bytes | str) -> None:
        arcname = f"{self.root_path}/{path}"
        self.zipfd.writestr(arcname, data)

    @classmethod
    @contextmanager
    def open(cls, dst: str | os.PathLike[str], root_path: str) -> Iterator[ZipArchive]:
        with atomic_write(dst) as fp:
            with ZipFile(fp, "w", compression=ZIP_DEFLATED) as zipfd:
                yield cls(zipfd, root_path)


class ZippedDirectoryBuilder(BuilderInterface):
    PLUGIN_NAME = "zipped-directory"

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

        with ZipArchive.open(target, install_name) as archive:
            for included_file in self.recurse_included_files():
                archive.add_file(included_file)
            archive.write_file(
                "METADATA.json",
                json.dumps(json_metadata_2_1(self.metadata), indent=2),
            )
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
