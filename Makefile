# SPDX-License-Identifier: GPL-3.0-only

SYSTEM_PYTHON ?= python3
PYTHON ?= venv/bin/python

.PHONY: setup run test coverage check

## Venv, dev tools, git hooks, and a .env with a new SENDER_HASH_KEY if missing.
setup:
	$(SYSTEM_PYTHON) -m venv venv
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pre_commit install
	test -f .env || sed "s/^SENDER_HASH_KEY=$$/SENDER_HASH_KEY=$$(openssl rand -hex 32)/" template.env >.env

## Serve on 127.0.0.1:16100, reloading on changes.
run:
	$(PYTHON) -m uvicorn gateway_client.app:app --port 16100 --reload

test:
	$(PYTHON) -m pytest $(PYTEST_ARGS)

## Run the tests with a coverage report.
coverage:
	$(PYTHON) -m pytest --cov $(PYTEST_ARGS)

check:
	$(PYTHON) -m pre_commit run --all-files --show-diff-on-failure
