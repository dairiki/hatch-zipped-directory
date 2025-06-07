## Changes

### 0.2.1 (2025-06-06)

#### Bugs Fixed

- Timestamps of parent directory entries are now set to the correct
  magic value with reproducible builds are enabled. ([#5], [#6])

#### Tests Fixed

- The functional test (`test_functional.py`) was testing the latest
  version of our plugin from PyPI rather than from local source.

- The CI tests appear to have been running whatever version of python
  was compiled into the installed `hatch` binary, rather than the system
  default python.

[#5]: https://github.com/dairiki/hatch-zipped-directory/issues/5
[#6]: https://github.com/dairiki/hatch-zipped-directory/pull/6

### 0.2.0 (2025-03-11)

#### Features

- Write parent directory entries to zip archive. Python requires this
  when importing modules directly from a zip archive. ([#4] — thank
  you @PolyPik)

#### Breaking Changes

- Drop support for Python 3.7 & 3.8.

#### Bugs Fixed

- (typing) `atomic_open` returns `io.BufferedRandom` (not `io.BufferedWriter`).

#### Tests

- Test under python 3.14.
- Test under windows.

[#4]: https://github.com/dairiki/hatch-zipped-directory/pull/4

### 0.1.0 (2023-12-12)

#### Bitrot

- Fix for hatchling 1.19 (hatch 1.8). `BuilderInterface.build`
  arguments are now all kw-only. ([hatch/6c252f8])

[hatch/6c252f8]: https://github.com/pypa/hatch/commit/6c252f8b8a65711846a6060c3d54f02936da2aa0)

### 0.1.0b4 (2023-09-10)

#### Features

- Add support for [reproducible builds] which are now enabled by
  default. When enabled, timestamps in the zip archive are set to a
  fixed value (configurable via the `SOURCE_DATE_EPOCH` environment
  variable) and the UNIX access modes of archive members are
  [normalized to either 0644 or 0755][mode-normalization] depending on
  whether the file is executable or not.

[reproducible builds]: https://hatch.pypa.io/latest/config/build/#reproducible-builds
[mode-normalization]: https://github.com/pypa/flit/pull/66

### 0.1.0b3 (2023-05-10)

#### Features

- Refactor JSON metadata code. Now we use `hatchling` to generate
  conventionall RFC 822-formatted distribution metadata, then convert
  that to JSON, explicitly following the steps outline in [PEP
  566](https://peps.python.org/pep-0566/#json-compatible-metadata).
  Among other things, this allows configuration of the
  *Metadata-Version* by setting
  `tool.hatch.build.targets.zipped-directory.core-metadata-version`.

#### Tests

- We now have 100% test coverage.

### 0.1.0b2 (2023-01-10)

#### Features

- The prefixing of file names under a top-level directory in the zip
  archive can now be disabled by setting `install-name = ""`.
  Thank you @gwerbin([#1][])

#### Bugs

- Use explicit encoding in hatch metadata hook (for Windows).

[#1]: https://github.com/dairiki/hatch-zipped-directory/issues/1

### 0.1.0b1 (2022-10-07)

Initial release.
