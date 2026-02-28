#!/bin/bash
# Launch the Movie Media Manager GUI application

REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 1
cd "$REPO_ROOT" || exit 1

source source_me.sh
python3 movie_organizer_gui.py "$@"
