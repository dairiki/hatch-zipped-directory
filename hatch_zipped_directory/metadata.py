from __future__ import annotations

from hatchling.metadata.core import ProjectMetadata

__all__ = ["json_metadata_2_1"]


def json_metadata_2_1(metadata: ProjectMetadata) -> dict[str, str | list[str]]:
    data = {
        "metadata_version": "2.1",
        "name": metadata.core.raw_name,
        "version": metadata.version,
    }
    if metadata.core.description:
        data["summary"] = metadata.core.description
    if metadata.core.urls:
        data["project_url"] = [
            f"{label}, {url}" for label, url in metadata.core.urls.items()
        ]
    for author, author_data in [
        ("author", metadata.core.authors_data),
        ("maintainer", metadata.core.maintainers_data),
    ]:
        if author_data["name"]:
            data[author] = ", ".join(author_data["name"])
        if author_data["email"]:
            data[f"{author}_email"] = ", ".join(author_data["email"])
    if metadata.core.license:
        data["license"] = metadata.core.license
    if metadata.core.license_files:
        data["license_file"] = metadata.core.license_files
    if metadata.core.keywords:
        data["keywords"] = metadata.core.keywords
    if metadata.core.classifiers:
        data["classifier"] = metadata.core.classifiers
    if metadata.core.requires_python:
        data["requires_python"] = metadata.core.requires_python

    requires_dist = []
    if metadata.core.dependencies:
        requires_dist.extend(metadata.core.dependencies)
    # FIXME: extra_dependencies?
    if metadata.core.optional_dependencies:
        data["provides-extra"] = list(metadata.core.optional_dependencies.keys())
        requires_dist.extend(
            _add_environment_marker(dependency, f"extra == {option!r}")
            for option, dependencies in metadata.core.optional_dependencies.items()
            for dependency in dependencies
        )
    if requires_dist:
        data["requires_dist"] = requires_dist

    if metadata.core.readme:
        data["description_content_type"] = metadata.core.readme_content_type
        data["description"] = metadata.core.readme

    return data


def _add_environment_marker(dependency: str, marker: str) -> str:
    if ";" in dependency:
        return f"{dependency} and {marker}"
    return f"{dependency} ; {marker}"
