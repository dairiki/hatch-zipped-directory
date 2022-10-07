import pytest

from hatch_zipped_directory.utils import atomic_write


def test_atomic_write(tmp_path):
    dst = tmp_path / "testfile.txt"

    with atomic_write(dst) as fp:
        fp.write(b"data")
        assert not dst.exists()
    assert dst.read_bytes() == b"data"
    assert set(tmp_path.iterdir()) == {dst}


def test_atomic_write_failure(tmp_path):
    dst = tmp_path / "testfile.txt"

    with pytest.raises(RuntimeError):
        with atomic_write(dst) as fp:
            fp.write(b"data")
            raise RuntimeError()
    assert set(tmp_path.iterdir()) == set()


def test_atomic_write_replace(tmp_path):
    dst = tmp_path / "testfile.txt"
    dst.write_bytes(b"orig")

    with atomic_write(dst) as fp:
        fp.write(b"data")
        assert dst.read_bytes() == b"orig"
    assert dst.read_bytes() == b"data"
    assert set(tmp_path.iterdir()) == {dst}


def test_atomic_write_replace_failure(tmp_path):
    dst = tmp_path / "testfile.txt"
    dst.write_bytes(b"orig")

    with pytest.raises(RuntimeError):
        with atomic_write(dst) as fp:
            fp.write(b"data")
            raise RuntimeError("test")
    assert dst.read_bytes() == b"orig"
    assert set(tmp_path.iterdir()) == {dst}
