PYTHON_VERSIONS = 3.10 3.11 3.12 3.13 3.14 3.15

.PHONY: default all pytest lint pytest-% cover-clean cover

default: pytest

all: lint cover

pytest:
	uv run pytest tests -ra

lint:
	prek run -a
	uv run mypy

cover: $(addprefix pytestcov-, ${PYTHON_VERSIONS})
	uv run coverage combine
	uv run coverage report --show-missing --fail-under=100

pytestcov-%: cover-clean
	uv run --isolated --python=$* --no-dev --group=test coverage run -m pytest tests

cover-clean:
	uv run coverage erase
