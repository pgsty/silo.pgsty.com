HUGO ?= hugo
PYTHON ?= python3
CHECK_PYTHON := .venv-check/bin/python

.PHONY: dev serve build check test

dev:
	HUGO_MODULE_REPLACEMENTS='github.com/pgsty/oink -> $(abspath ../oink)' $(HUGO) server --renderToMemory

serve:
	$(HUGO) server --environment production --minify --disableFastRender --disableLiveReload

build:
	$(HUGO) build --minify --cleanDestinationDir

.venv-check/installed: bin/requirements-test.txt
	$(PYTHON) -m venv .venv-check
	$(CHECK_PYTHON) -m pip install -r bin/requirements-test.txt
	touch $@

test: .venv-check/installed
	$(CHECK_PYTHON) -m unittest discover -s bin -p 'test_*.py'

check: test
	go mod verify
	$(HUGO) build --minify --cleanDestinationDir --printPathWarnings --printI18nWarnings --panicOnWarning
	python3 bin/check_internal_links.py public
