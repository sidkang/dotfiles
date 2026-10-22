#!/usr/bin/env bash
set -euo pipefail

service="gui/$(id -u)/com.sid.kitten"
plist="$HOME/Library/LaunchAgents/com.sid.kitten.plist"

# Validate before stopping the running instance.
plutil -lint "$plist"
if launchctl print "$service" >/dev/null 2>&1; then
    launchctl bootout "$service"
fi
launchctl bootstrap "gui/$(id -u)" "$plist"
