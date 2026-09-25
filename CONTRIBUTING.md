# Contributing to textrieve

Thanks for considering a contribution. Keep it small and reviewable.

- **Bugs / ideas:** open an issue before a PR.
- **Code style:** match the existing pure-Python (no framework helpers in `ocr.py`), keep `ocr.py` dependency-light.
- **Tests:** run `python -m pytest -q` — the suite generates its own fixtures; nothing external.
- **New dependencies:** justify them; the core runs on CPU for free-tier hosting.
- **License:** Apache-2.0, like the rest of the project.

Commit sign-off is not required, but authorship should be your real GitHub identity.