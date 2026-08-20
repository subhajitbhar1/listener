"""Thin entry so `python main.py` still works. Prefer `python -m listener`."""

from listener.__main__ import main

if __name__ == "__main__":
    main()
