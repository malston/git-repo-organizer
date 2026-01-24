# ABOUTME: Developer Makefile for gro (Git Repository Organizer).
# ABOUTME: Provides common development tasks using uv for package management.

.PHONY: help install dev test lint format typecheck check clean build

# Default target
help:
	@echo "gro - Git Repository Organizer"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup:"
	@echo "  install     Install production dependencies"
	@echo "  dev         Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  test        Run tests with coverage"
	@echo "  lint        Run ruff linter"
	@echo "  format      Format code with ruff"
	@echo "  typecheck   Run mypy type checker"
	@echo "  check       Run all checks (lint, typecheck, test)"
	@echo ""
	@echo "Build:"
	@echo "  build       Build package"
	@echo "  clean       Remove build artifacts"
	@echo ""
	@echo "Run:"
	@echo "  run         Run gro CLI (use ARGS to pass arguments)"
	@echo "              Example: make run ARGS='status'"

# Installation
install:
	uv tool install --force .

dev:
	uv sync

# Testing
test:
	uv run pytest

test-verbose:
	uv run pytest -v --tb=short

test-fast:
	uv run pytest -x --tb=short

# Linting and formatting
lint:
	uv run ruff check src tests

lint-fix:
	uv run ruff check --fix src tests

format:
	uv run ruff format src tests

format-check:
	uv run ruff format --check src tests

# Type checking
typecheck:
	uv run mypy src

# Run all checks
check: lint typecheck test

# Building
build:
	uv build

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf __pycache__/
	rm -rf src/gro/__pycache__/
	rm -rf tests/__pycache__/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Run the CLI
ARGS ?=
run:
	uv run gro $(ARGS)

# Development shortcuts
.PHONY: init status apply sync add

init:
	uv run gro init $(ARGS)

status:
	uv run gro status $(ARGS)

apply:
	uv run gro apply $(ARGS)

sync:
	uv run gro sync $(ARGS)

add:
	uv run gro add $(ARGS)
