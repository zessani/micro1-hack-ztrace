.PHONY: setup test

setup:
	python3 scripts/generate_config.py
	python3 scripts/migrate.py
	python3 scripts/reset_fixtures.py

test:
	pytest
