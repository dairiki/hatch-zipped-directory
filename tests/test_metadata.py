import inspect

import pytest

from hatch_zipped_directory.metadata import metadata_to_json


REQUIRED_METADATA = (
    inspect.cleandoc(
        """
        Metadata-Version: 42.2
        Name: dummy-test-project
        Version: 0.1a1
        """
    )
    + "\n"
)

REQUIRED_METADATA_JSON = {
    "metadata_version": "42.2",
    "name": "dummy-test-project",
    "version": "0.1a1",
}


def test_metadata_to_json() -> None:
    assert metadata_to_json(REQUIRED_METADATA) == REQUIRED_METADATA_JSON


@pytest.mark.parametrize(
    "field_name",
    [
        "Dynamic",
        "Platform",
        "Supported-Platform",
        "Classifier",
        "Requires-Dist",
        "Requires-External",
        "Project-URL",
        "Provides-Extra",
        "Provides-Dist",
        "Obsoletes-Dist",
        "License-File",
    ],
)
def test_metadata_to_json_multi_use_field(field_name: str) -> None:
    metadata = REQUIRED_METADATA + inspect.cleandoc(
        f"""
        {field_name}: v1
        {field_name.upper()}: v2
        {field_name.lower()}: v3
        """
    )
    json_key = field_name.lower().replace("-", "_")
    expected: dict[str, str | list[str]] = {
        **REQUIRED_METADATA_JSON,
        json_key: ["v1", "v2", "v3"],
    }
    assert metadata_to_json(metadata) == expected


def test_metadata_to_json_duplicate_single_use_field() -> None:
    metadata = REQUIRED_METADATA + inspect.cleandoc(
        """
        SUMMARY: summary1
        Summary: summary2
        summary: summary3
        """
    )
    expected: dict[str, str | list[str]] = {
        **REQUIRED_METADATA_JSON,
        "summary": "summary1",
    }
    assert metadata_to_json(metadata) == expected


def test_metadata_to_json_keywords() -> None:
    metadata = REQUIRED_METADATA + "Keywords:   kw1,key word 2, kw3\n"
    expected: dict[str, str | list[str]] = {
        **REQUIRED_METADATA_JSON,
        "keywords": ["kw1", "key word 2", " kw3"],
    }
    assert metadata_to_json(metadata) == expected


def test_metadata_to_json_dedent() -> None:
    metadata = REQUIRED_METADATA + inspect.cleandoc(
        """
        License: Copyright
            To wit:
                - Important
        """
    )
    expected: dict[str, str | list[str]] = {
        **REQUIRED_METADATA_JSON,
        "license": "Copyright\nTo wit:\n    - Important",
    }
    assert metadata_to_json(metadata) == expected


def test_metadata_to_json_description() -> None:
    description = (
        inspect.cleandoc(
            """
            Description
            ===========

            Here is a description.
            """
        )
        + "\n"
    )
    metadata = REQUIRED_METADATA + "\n" + description
    expected: dict[str, str | list[str]] = {
        **REQUIRED_METADATA_JSON,
        "description": description,
    }
    assert metadata_to_json(metadata) == expected
