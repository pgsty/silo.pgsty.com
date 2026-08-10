HUGO ?= hugo

# An ignored sibling-theme workspace is opt-in for local development. Normal
# checkouts without go.work continue to use the OINK version pinned in go.mod.
ifneq ($(wildcard go.work),)
HUGO_MODULE_WORKSPACE ?= go.work
export HUGO_MODULE_WORKSPACE
endif

.PHONY: dev build check

dev:
	$(HUGO) server

build:
	$(HUGO) build --minify --cleanDestinationDir

check:
	go mod verify
	$(HUGO) build --minify --cleanDestinationDir --printPathWarnings --printI18nWarnings --panicOnWarning
	python3 bin/check_internal_links.py public
