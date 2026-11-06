#!/bin/sh

while ! ~/nsh/easy-screenshot/run.sh -A Python; do sleep 0.7; done; \
osascript -e 'tell application "Python" to quit'
