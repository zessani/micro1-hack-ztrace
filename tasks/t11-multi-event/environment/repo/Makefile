.PHONY: setup dev prepare test

setup:
	python3 scripts/generate_config.py
	python3 scripts/migrate.py
	python3 scripts/reset_fixtures.py

dev:
	pip install -v -e .

prepare:
	python3 scripts/prepare.py

test:
	pytest
