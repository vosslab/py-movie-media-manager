#!/bin/sh

REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 1
"$REPO_ROOT/launch_gui.sh" >/tmp/movie.log 2>&1 & \
sleep 2
while ! ~/nsh/easy-screenshot/run.sh -A Python; do sleep 0.7; done; \
osascript -e 'tell application "Python" to quit'
