from __future__ import annotations

import json
import os
import types
from contextlib import ExitStack
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from typing import Callable
from typing import Iterable
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from hatchling.builders.plugin.interface import BuilderInterface
from hatchling.builders.plugin.interface import IncludedFile
from hatchling.builders.utils import normalize_relative_path
from hatchling.builders.utils import replace_file

from .metadata import json_metadata_2_1

__all__ = ["InkscapeExtensionBuilder"]


class ZipArchive:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self._close = None
        self.path = None
        with ExitStack() as stack:
            fd = stack.enter_context(NamedTemporaryFile(delete=False))
            self.zipfd = stack.enter_context(ZipFile(fd, "w", compression=ZIP_DEFLATED))
            self._close = stack.pop_all().close
            self.path = fd.name

    def __enter__(self) -> ZipArchive:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        if callable(self._close):
            self._close()
            self._close = None
            if exc_value and self.path is not None:
                try:
                    os.unlink(self.path)
                except FileNotFoundError:
                    pass
                self.path = None

    def add_file(self, included_file: IncludedFile) -> None:
        arcname = f"{self.root_path}/{included_file.distribution_path}"
        self.zipfd.write(included_file.path, arcname=arcname)

    def write_file(self, path: str, data: bytes | str) -> None:
        arcname = f"{self.root_path}/{path}"
        self.zipfd.writestr(arcname, data)


class InkscapeExtensionBuilder(BuilderInterface):
    PLUGIN_NAME = "inkscape-extension"

    def get_version_api(self) -> dict[str, Callable[..., str]]:
        return {"standard": self.build_standard}

    def clean(self, directory: str, versions: Iterable[str]) -> None:
        for filename in os.listdir(directory):
            if filename.endswith(".zip"):
                os.remove(os.path.join(directory, filename))

    def build_standard(self, directory: str, **build_data: Any) -> str:
        project_name = self.normalize_file_name_component(
            self.metadata.core.raw_name
        )
        if "install-name" in self.target_config:
            install_name = self.target_config["install-name"]
        else:
            install_name = project_name

        with ZipArchive(install_name) as archive:
            for included_file in self.recurse_included_files():
                archive.add_file(included_file)
            archive.write_file(
                "METADATA.json",
                json.dumps(json_metadata_2_1(self.metadata), indent=2),
            )

        target = Path(directory, f"{project_name}-{self.metadata.version}.zip")
        replace_file(archive.path, target)
        return os.fspath(target)

    def get_default_build_data(self) -> dict[str, Any]:
        build_data: dict[str, Any] = super().get_default_build_data()
        extra_files = []
        if self.metadata.core.readme_path:
            extra_files.append(self.metadata.core.readme_path)
        if self.metadata.core.license_files:
            extra_files.extend(self.metadata.core.license_files)

        if extra_files:
            force_include = build_data.setdefault("force_include", {})
            for fn in map(normalize_relative_path, extra_files):
                force_include[os.path.join(self.root, fn)] = Path(fn).name

        return build_data
