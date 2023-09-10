# hatch-zipped-directory

[![PyPI - Version](https://img.shields.io/pypi/v/hatch-zipped-directory.svg)](https://pypi.org/project/hatch-zipped-directory)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/hatch-zipped-directory.svg)](https://pypi.org/project/hatch-zipped-directory)
[![Tests](https://github.com/dairiki/hatch-zipped-directory/actions/workflows/tests.yml/badge.svg)](https://github.com/dairiki/hatch-zipped-directory/actions/workflows/tests.yml)
[![Trackgit Views](https://us-central1-trackgit-analytics.cloudfunctions.net/token/ping/lhautvz4zffrt8jawcpl)](https://trackgit.com)

-----

This is a [Hatch](https://hatch.pypa.io/latest/) plugin that provides
a custom builder to support building zip archives for quasi-manual
installation into various foreign package installation systems.
(Specifically, I use this for packaging
[Inkscape](https://inkscape.org/) extensions and symbols libraries,
but it may be useful in other contexts, such as deploying to cloud
compute platforms.)

The builder creates a zip archive.  All the contents of the zip
archive will be included under a single specific top-level directory.
The default name of the top-level directory is a file-name-safe
version of the project name, however the name of the directory may be
configured by setting the `install-name` key in the target-specific
configuration section.
This behavior may be disabled by setting `install-name = ''`.

In addition to whatever files are selected for inclusion in the
archive via Hatch’s regular [build configuration
settings](https://hatch.pypa.io/latest/config/build/), any configured
project README and license files will be included in the top level of
the install directory within the zip archive.

As well, a `METADATA.json` file containing the project metadata in
JSON format (as described in
[PEP 566](https://peps.python.org/pep-0566/#json-compatible-metadata))
will be included in the top level of the install directory within the
zip archive.


## Example

Assume a project source directory looking something like:
```
.
├── pyproject.toml
├── LICENSE.txt
├── README.md
├── src
│   ├── subdir
│   │   ├── data.txt
│   │   └── more-code.py
│   └── my-code.py
└── tests
    └── test_foo.py
```

Where `pyproject.toml` looks like:
```toml
[build-system]
requires = [
    "hatchling",
    "hatch-zipped-directory",
]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.42"

[tool.hatch.build.targets.zipped-directory]
install-name = "org.example.test"
sources = [
    "/src",
]
```

Then, running
```sh
hatch build --target zipped-directory
```

will build a zip archive named `dist/test_project-0.42.zip` with the following
structure:
```
.
└── org.example.test
    ├── LICENSE.txt
    ├── METADATA.json
    ├── README.md
    ├── my-code.py
    └── subdir
        ├── data.txt
        └── more-code.py
```

## Reproducible Builds

By default, this plugin attempts to build [reproducible][reproducible
builds] archives by setting the timestamps of the zip entries to a
fixed value. When building in reproducible mode, the UNIX file modes
of the archive entries is also normalized (to either 0644 or 0755
depending on whether the file is executable.)

The timestamp used for reproducible builds may be configured by
setting the `SOURCE_DATE_EPOCH` environment variable.

Reproducible builds may be disabled by setting `reproducible = false`
in an appropriate section of `pyproject.toml` or `hatch.toml`.  See
Hatch’s documentation on [Build Configuration] for details.


## Author

Jeff Dairiki <dairiki@dairiki.org>

## License

`hatch-zipped-directory` is distributed under the terms of the
[MIT](https://spdx.org/licenses/MIT.html) license.

[reproducible builds]: https://hatch.pypa.io/latest/config/build/#reproducible-builds
[Build Configuration]: https://hatch.pypa.io/latest/config/build/
