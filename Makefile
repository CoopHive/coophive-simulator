#* Variables
PYTHON := python3

#* Poetry
.PHONY: poetry-download
poetry-download:
	curl -sSL https://install.python-poetry.org | $(PYTHON) -
    
.PHONY: poetry-remove
poetry-remove:
	curl -sSL https://install.python-poetry.org | $(PYTHON) - --uninstall

.PHONY: install
install:
	rm -f poetry.lock
	poetry install -n
	poetry run pre-commit install

.PHONY: codestyle
codestyle:
	poetry run isort --settings-path pyproject.toml ./
	poetry run black --config pyproject.toml ./

.PHONY: check-codestyle
check-codestyle:
	poetry run isort --diff --check-only --settings-path pyproject.toml ./
	poetry run black --diff --check --config pyproject.toml ./

.PHONY: docs
docs:
	poetry run pydocstyle --convention=google .

.PHONY: test
test:
	poetry run pytest -c pyproject.toml tests/

.PHONY: diagrams
diagrams:
	pyreverse coophive -A --colorized -p coophive -d docs/img -o dot
	python3 docs/classes_filter.py
	dot -Tpng docs/img/classes_coophive.dot -o docs/img/classes_coophive.png
	dot -Tpng docs/img/packages_coophive.dot -o docs/img/packages_coophive.png

.PHONY: flush
flush:
	./kill_processes.sh
