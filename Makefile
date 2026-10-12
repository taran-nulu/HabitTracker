PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
APP := dist/Habit Tracker.app
APP_NAME := Habit Tracker.app

.PHONY: help setup run icon build install clean distclean

help:
	@echo "make setup    - create .venv and install dependencies"
	@echo "make run      - run the app from source"
	@echo "make icon     - regenerate HabitTracker.icns from app_icon.PNG"
	@echo "make build    - build '$(APP)'"
	@echo "make install  - copy the built app to /Applications"
	@echo "make clean    - remove build artifacts"

$(BIN)/python:
	$(PY) -m venv $(VENV)

setup: $(BIN)/python
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

run:
	@if [ -x "$(BIN)/python" ]; then \
		$(BIN)/python main.py; \
	else \
		echo "no venv found; run 'make setup' first"; exit 1; \
	fi

icon:
	bash tools/make_icon.sh

build: setup icon
	rm -rf build dist
	$(BIN)/python setup.py py2app
	@echo ""
	@echo "Built $(APP)"
	@codesign -dv "$(APP)" 2>&1 | grep -E 'Signature|Identifier' || true

install: build
	rm -rf "/Applications/$(APP_NAME)"
	ditto "$(APP)" "/Applications/$(APP_NAME)"
	codesign --force --sign - "/Applications/$(APP_NAME)"
	@echo "Installed to /Applications/$(APP_NAME)"

clean:
	rm -rf build dist
	rm -f HabitTracker.icns
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +

distclean: clean
	rm -rf $(VENV)