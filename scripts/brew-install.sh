#!/usr/bin/env bash
# Usage: brew-install.sh BREWFILE [NAME...]
# Install every entry in BREWFILE, or only the entries whose last path segment matches a NAME.
set -euo pipefail

file=$1
shift

if [ $# -eq 0 ]; then
  brew bundle install --no-upgrade --file="$file"
  exit
fi

subset=$(mktemp)
trap 'rm -f "$subset"' EXIT
for name in "$@"; do
  grep -E "^(brew|cask) \"([^\"]*/)?$name\"" "$file" >>"$subset" || {
    echo "Not in $file: $name" >&2
    exit 1
  }
done
brew bundle install --no-upgrade --file="$subset"
