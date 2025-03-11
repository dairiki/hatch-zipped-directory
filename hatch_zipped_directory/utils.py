from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_write(dst: str | os.PathLike[str]) -> Iterator[io.BufferedRandom]:
    dst_path = Path(dst)
    fd, tmp_path = tempfile.mkstemp(dir=dst_path.parent, suffix=dst_path.suffix)
    try:
        with open(fd, mode="w+b") as fp:
            yield fp
        os.replace(tmp_path, dst_path)
    except BaseException:
        os.unlink(tmp_path)
        raise
