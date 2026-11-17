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
      // (if .model != null then "auto" else "" end)
      | ascii_downcase
    ),
    (.agent.name // ""),
    (.workspace.current_dir // .cwd // ""),
    ((.context_window.used_percentage // 0) | round | tostring),
    ((.context_window.context_window_size // 0) | tostring),
    ((.context_window.total_input_tokens // 0) | tostring),
    ((.context_window.total_output_tokens // 0) | tostring),
    (if .exceeds_200k_tokens == true then "1" else "0" end)
  ] | join("\u001f")
' 2>/dev/null) || exit 0

IFS="$us" read -r model effort agent dir used_pct ctx_size in_tok out_tok exceeds_200k <<EOF
$parsed
EOF

fmt_tok() {
  n=$1
  if [ "$n" -ge 1000000 ] 2>/dev/null; then
    awk -v n="$n" 'BEGIN { printf "%.1fM", n / 1000000 }'
  elif [ "$n" -ge 1000 ] 2>/dev/null; then
    awk -v n="$n" 'BEGIN { printf "%.1fk", n / 1000 }'
  else
    printf '%s' "${n:-0}"
  fi
}

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

# Detect jj or git repository without taking a working-copy lock.
vcs_info=""
if [ -n "$dir" ] && [ -d "$dir" ]; then
  probe="$dir"
  vcs_kind=""
  while :; do
    if [ -d "$probe/.jj" ]; then
      vcs_kind="jj"
      break
    elif [ -e "$probe/.git" ]; then
      vcs_kind="git"
      break
    fi
    [ "$probe" = "/" ] && break
    probe=$(dirname "$probe")
  done

  if [ "$vcs_kind" = "jj" ] && command -v jj >/dev/null 2>&1; then
    jj_ref=$(jj -R "$dir" --ignore-working-copy log -r '@' --no-graph \
      -T 'coalesce(bookmarks.join(","), change_id.shortest(6)) ++ if(empty, "", "*")' 2>/dev/null)
    [ -n "$jj_ref" ] && vcs_info="jj:$jj_ref"
  elif [ "$vcs_kind" = "git" ] && command -v git >/dev/null 2>&1; then
    git_ref=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ -n "$git_ref" ]; then
      if [ -n "$(git -C "$dir" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
        git_ref="${git_ref}*"
      fi
      vcs_info="git:$git_ref"
    fi
  fi
fi

# Context window bar (8 cells) & threshold color.
filled=$(( (used_pct * 8 + 50) / 100 ))
[ "$filled" -gt 8 ] && filled=8
[ "$filled" -lt 0 ] && filled=0
empty=$((8 - filled))

bar=""
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

esc=$(printf '\033')
c_reset="${esc}[0m"
c_dim="${esc}[2m"
c_model="${esc}[1;34m"
c_effort="${esc}[33m"
c_agent="${esc}[35m"
c_dir="${esc}[36m"
c_vcs="${esc}[35m"

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
if [ "$effort" = "auto" ]; then
  out="${out} ${c_dim}[auto]${c_reset}"
elif [ -n "$effort" ]; then
  out="${out} ${c_effort}[${effort}]${c_reset}"
fi

if [ -n "$agent" ]; then
  out="${out}${sep}${c_agent}@${agent}${c_reset}"
fi

if [ "$ctx_size" -gt 0 ] 2>/dev/null; then
  out="${out}${sep}${ctx_color}[${bar}] ${used_pct}%${c_reset}"
fi

if [ "${in_tok:-0}" -gt 0 ] || [ "${out_tok:-0}" -gt 0 ]; then
  in_fmt=$(fmt_tok "$in_tok")
  out_fmt=$(fmt_tok "$out_tok")
  out="${out} ${c_dim}↑${in_fmt} ↓${out_fmt}${c_reset}"
fi

if [ -n "$short_dir" ]; then
  out="${out}${sep}${c_dir}${short_dir}${c_reset}"
fi

if [ -n "$vcs_info" ]; then
  out="${out} ${c_vcs}(${vcs_info})${c_reset}"
fi

printf '%s\n' "$out"
