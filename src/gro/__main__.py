# ABOUTME: Entry point for running gro as a module (python -m gro).
# ABOUTME: Delegates to the CLI main function.
"""Allow running as python -m gro."""

from gro.cli import main

if __name__ == "__main__":
    main()
