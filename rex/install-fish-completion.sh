#!/usr/bin/env bash
# Generate the Fish completion wrapper for rex.
# The wrapper calls `rex __complete` at runtime, so most CLI changes do not
# need a regen; rewrite when the wrapper text or Rex version changes.
set -euo pipefail

if [[ $# -gt 0 ]]; then
  echo "usage: $0" >&2
  exit 2
fi

resolve_rex() {
  local candidates=(
    "/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex"
    "/Applications/Rex.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  if command -v rex >/dev/null 2>&1; then
    command -v rex
    return 0
  fi
  echo "rex not found (Rex Beta.app, Rex.app, or PATH)" >&2
  return 1
}

rex_bin="$(resolve_rex)"
version="$("$rex_bin" version --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["rex_version"])')"
out_dir="${HOME}/.config/fish/completions"
out_file="${out_dir}/rex.fish"
stamp_file="${out_file}.version"
tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

"$rex_bin" completion fish >"$tmp_file"
mkdir -p "$out_dir"

current_version=""
if [[ -f "$stamp_file" ]]; then
  current_version="$(<"$stamp_file")"
fi

if [[ -f "$out_file" ]] && cmp -s "$tmp_file" "$out_file" && [[ "$current_version" == "$version" ]]; then
  echo "unchanged: $out_file ($version)"
  exit 0
fi

cp "$tmp_file" "$out_file"
printf '%s\n' "$version" >"$stamp_file"
echo "wrote $out_file ($version)"
