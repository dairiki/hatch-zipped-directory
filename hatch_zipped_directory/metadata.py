from __future__ import annotations

import email
import textwrap
from email.message import Message

__all__ = ["metadata_to_json"]


_MULTIPLE_USE_KEYS = {
    key.lower()
    for key in [
        # PEP 345 (1.2)
        "Platform",
        "Supported-Platform",
        "Classifier",
        "Requires-Dist",
        "Provides-Dist",
        "Obsoletes-Dist",
        "Requires-External",
        "Project-URL",
        # PEP 566 (2.1)
        "Provides-Extra",
        # PEP 643
        "Dynamic",
        # PEP 639
        "License-File",
    ]
}


def _dedent(value: str) -> str:
    """Fix RFC 822 indentation.

    Dedent all but first line.
    """
    first, nl, rest = value.partition("\n")
    if not nl:
        return value
    return first + nl + textwrap.dedent(rest)


def _get_value(headers: Message, key: str) -> str | list[str]:
    lkey = key.lower()
    if lkey in _MULTIPLE_USE_KEYS:
        return list(map(_dedent, headers.get_all(key, [])))
    elif lkey == "keywords":
        return _dedent(headers[key]).split(",")
    return _dedent(headers[key])


def metadata_to_json(metadata: str) -> dict[str, str | list[str]]:
    """Convert metadata text to JSON as described in `PEP 566`__.

    __ https://peps.python.org/pep-0566/#json-compatible-metadata
    """
    headers = email.message_from_string(metadata)
    assert not headers.is_multipart()
    description = headers.get_payload()

    data: dict[str, str | list[str]] = {}
    for key in headers:
        json_key = key.lower().replace("-", "_")
        if json_key not in data:
            data[json_key] = _get_value(headers, key)

    if description:
        data["description"] = description

    return data
