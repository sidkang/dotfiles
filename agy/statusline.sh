#!/bin/sh
# Custom status line for Antigravity CLI (agy).
# Reads session state JSON from stdin and prints a single ANSI-colored line
# tuned for light terminal backgrounds.

PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

input=$(cat)
[ -z "$input" ] && exit 0

us=$(printf '\037')
parsed=$(printf '%s' "$input" | jq -r '
  [
    ((.model.display_name // .model.id // "no model") | sub(" \\((?i:low|medium|high|xhigh|max)\\)$"; "")),
    (
      .model.effort
      // .effort
      // .reasoning_effort
      // (try ((.model.display_name // "") | capture(" \\((?<e>(?i:low|medium|high|xhigh|max))\\)$").e) catch null)
      // (try ((.model.id // "") | capture("-(?<e>(?i:low|medium|high|xhigh|max))$").e) catch null)
      // ""
      | ascii_downcase
    ),
    (.agent.name // ""),
    (.cycle_mode // ""),
    (.workspace.current_dir // .cwd // ""),
    ((.context_window.used_percentage // 0) | round | tostring),
    ((.context_window.context_window_size // 0) | tostring),
    (if .exceeds_200k_tokens == true then "1" else "0" end),
    (([.subagents[]? | select(.status == "running")] | length) | tostring),
    ((.task_count // 0) | tostring),
    ((.pending_input_count // 0) | tostring),
    (if .sandbox.enabled == true then "1" else "0" end),
    ((.terminal_width // 0) | tostring)
  ] | join("\u001f")
' 2>/dev/null) || exit 0

IFS="$us" read -r model effort agent cycle_mode dir used_pct ctx_size exceeds_200k running_subs task_count pending_count sandbox_on term_width <<EOF
$parsed
EOF

# Shorten directory path: replace $HOME with ~ and keep at most 3 trailing segments.
short_dir=""
if [ -n "$dir" ]; then
  case "$dir" in
    "$HOME") short_dir="~" ;;
    "$HOME"/*) short_dir="~/${dir#"$HOME"/}" ;;
    *) short_dir="$dir" ;;
  esac
  slash_count=$(printf '%s' "$short_dir" | tr -cd '/' | wc -c | tr -d ' ')
  if [ "$slash_count" -gt 3 ]; then
    p3=$(basename "$short_dir")
    d2=$(dirname "$short_dir")
    p2=$(basename "$d2")
    case "$short_dir" in
      "~"/*) short_dir="~/…/$p2/$p3" ;;
      *) short_dir="…/$p2/$p3" ;;
    esac
  fi
fi

# Context window bar (8 cells) & threshold color.
narrow=0
if [ "${term_width:-0}" -gt 0 ] 2>/dev/null && [ "$term_width" -lt 80 ] 2>/dev/null; then
  narrow=1
fi

bar=""
if [ "$narrow" = "0" ]; then
  filled=$(( (used_pct * 8 + 50) / 100 ))
  [ "$filled" -gt 8 ] && filled=8
  [ "$filled" -lt 0 ] && filled=0
  empty=$((8 - filled))

  i=0
  while [ "$i" -lt "$filled" ]; do
    bar="${bar}█"
    i=$((i + 1))
  done
  i=0
  while [ "$i" -lt "$empty" ]; do
    bar="${bar}░"
    i=$((i + 1))
  done
fi

esc=$(printf '\033')
c_reset="${esc}[0m"
c_dim="${esc}[2m"
c_model="${esc}[1;34m"
c_effort="${esc}[33m"
c_agent="${esc}[35m"
c_activity="${esc}[33m"
c_sandbox="${esc}[32m"
c_dir="${esc}[36m"

case "$cycle_mode" in
  auto) c_mode="${esc}[1;31m" ;;
  accept-edits) c_mode="${esc}[1;32m" ;;
  plan) c_mode="${esc}[1;35m" ;;
  *) c_mode="${esc}[1;36m" ;;
esac

if [ "$exceeds_200k" = "1" ] || [ "$used_pct" -ge 80 ]; then
  ctx_color="${esc}[31m"
elif [ "$used_pct" -ge 50 ]; then
  ctx_color="${esc}[33m"
else
  ctx_color="${esc}[32m"
fi

sep=" ${c_dim}│${c_reset} "

# Assemble segments.
out="${c_model}${model}${c_reset}"
if [ -n "$effort" ]; then
  out="${out} ${c_effort}[${effort}]${c_reset}"
fi

if [ -n "$cycle_mode" ]; then
  out="${out}${sep}${c_mode}${cycle_mode}${c_reset}"
fi

if [ -n "$agent" ]; then
  out="${out}${sep}${c_agent}@${agent}${c_reset}"
fi

if [ "$ctx_size" -gt 0 ] 2>/dev/null; then
  if [ "$narrow" = "1" ]; then
    out="${out}${sep}${ctx_color}${used_pct}%${c_reset}"
  else
    out="${out}${sep}${ctx_color}[${bar}] ${used_pct}%${c_reset}"
  fi
fi

activity=""
if [ "${running_subs:-0}" -gt 0 ] 2>/dev/null; then
  activity="${running_subs} sub"
fi
if [ "${task_count:-0}" -gt 0 ] 2>/dev/null; then
  activity="${activity:+${activity} }${task_count} task"
fi
if [ "${pending_count:-0}" -gt 0 ] 2>/dev/null; then
  activity="${activity:+${activity} }${pending_count} queued"
fi
if [ -n "$activity" ]; then
  out="${out}${sep}${c_activity}${activity}${c_reset}"
fi

if [ "$sandbox_on" = "1" ]; then
  out="${out}${sep}${c_sandbox}sandbox${c_reset}"
fi

if [ -n "$short_dir" ]; then
  out="${out}${sep}${c_dir}${short_dir}${c_reset}"
fi

printf '%s\n' "$out"
