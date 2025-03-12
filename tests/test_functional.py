import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture
def demo_path(tmp_path):
    path = tmp_path / "demo-project"
    shutil.copytree(Path(__file__).parent / "demo-project", path)
    return path


def test_build_demo(demo_path):
    subprocess.run(
        [sys.executable, "-m", "hatch", "build", "--target", "zipped-directory"],
        cwd=demo_path,
        env={**os.environ, "HATCH_ENV": "default"},
        check=True,
    )
    with ZipFile(demo_path / "dist/demo-0.42.zip") as zf:
        assert set(zf.namelist()) == {
            # from src/
            "org.example.test/code.py",
            "org.example.test/subdir/data.txt",
            # core metadata files
            "org.example.test/LICENSE.txt",
            "org.example.test/METADATA.json",
            "org.example.test/README.md",
        }
