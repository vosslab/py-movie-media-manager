## Repository guidance

- docs/REPO_STYLE.md
- docs/PYTHON_STYLE.md
- docs/MARKDOWN_STYLE.md
- docs/PYTEST_STYLE.md
- docs/CHANGELOG.md
- docs/HUMAN_GUIDANCE.md
- docs/DESIGN_DECISIONS.md
- When in doubt, implement the changes the user asked for rather than waiting for a response.
- Run focused pytest checks for changed code; use `-k` to narrow test selection when useful.

## Python environment

- AI agents run Python with `source source_me.sh && python3`.
- Add required PYTHONPATH entries to source_me.sh.
- Prefer the system Python; use Python 3.12 on macOS and 3.13 on Debian. Use a venv only as a last resort.
- macOS modules: `/opt/homebrew/lib/python3.12/site-packages/`; Debian modules: `/home/vosslab/.local/lib/python3.1x/site-packages/`.
