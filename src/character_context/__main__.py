"""Allow `python -m character_context` alongside the `charctx` entry point."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
