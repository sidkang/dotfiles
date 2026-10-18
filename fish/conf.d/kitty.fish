# Kitty integration: context user vars, worker helpers, and kitten abbreviations.
status is-interactive; or return

# Kitty context user-var schema:
# - All values are strings; empty means unknown/cleared.
# - PROGRAM is the coarse environment: local, ssh, ksh, zellij, pi, claude, codex.
# - CWD is an absolute path when known; PROJECT is the nearest .jj/.git root name.
# - *_UPDATED_AT is Unix epoch seconds; *_TTL is a duration in seconds.
# - Empty or 0 TTL means "no expiry". Writers should set *_OWNER to their name.
# - AGENT_* fields are reserved for coding-agent integrations, not shell guesses.
function __kitty_context_project
    set -l dir $PWD
    while test -n "$dir"; and test "$dir" != /
        if test -e "$dir/.jj"; or test -e "$dir/.git"
            basename "$dir"
            return 0
        end
        set dir (dirname "$dir")
    end
    return 1
end

function __kitty_context_set
    set -q KITTY_WINDOW_ID; or return 0
    command -q kitten; or return 0

    set -l program $argv[1]
    set -l host ""
    set -l session ""
    set -l command_name ""
    test (count $argv) -ge 2; and set host $argv[2]
    test (count $argv) -ge 3; and set session $argv[3]
    test (count $argv) -ge 4; and set command_name $argv[4]

    set -l cwd ""
    set -l project ""
    if test "$program" = local; or set -q SSH_CONNECTION; or set -q SSH_TTY
        set cwd $PWD
        set project (__kitty_context_project)
    end

    set -l updated_at (command date +%s 2>/dev/null)
    command kitten @ set-user-vars \
        "PROGRAM=$program" \
        "CWD=$cwd" \
        "PROJECT=$project" \
        "HOST=$host" \
        "SESSION=$session" \
        "COMMAND=$command_name" \
        CTX_OWNER=fish \
        "CTX_UPDATED_AT=$updated_at" \
        CTX_TTL= \
        AGENT= \
        AGENT_STATE= \
        AGENT_MODEL= \
        AGENT_PROVIDER= \
        AGENT_SESSION= \
        AGENT_TASK= \
        AGENT_CONTEXT= \
        AGENT_COST= \
        AGENT_TOOL= \
        AGENT_SUBAGENT= \
        AGENT_OWNER= \
        "AGENT_UPDATED_AT=$updated_at" \
        AGENT_TTL= >/dev/null 2>&1
end

function __kitty_context_idle --on-event fish_prompt
    if set -q SSH_CONNECTION; or set -q SSH_TTY
        set -l program ssh
        set -q KITTY_WINDOW_ID; and set program ksh
        __kitty_context_set $program $hostname
    else
        __kitty_context_set local
    end
end

function __ssh_context_host_from_args
    set -l skip_next 0
    set -l options_with_values b c D E F i J L l m O o p Q R S W w

    for arg in $argv
        if test $skip_next -eq 1
            set skip_next 0
            continue
        end
        if test "$arg" = --
            continue
        end
        if string match -q -- '-*' "$arg"
            set -l option (string replace -r '^--?' '' -- "$arg")
            contains -- $option $options_with_values; and set skip_next 1
            continue
        end
        string replace -r '^.*@' '' -- "$arg" | string replace -r '^\[([^\]]+)\].*' '$1' | string replace -r '[:/].*$' ''
        return 0
    end
end

function __zellij_session_from_args
    if test (count $argv) -eq 0
        set -q ZELLIJ_SESSION_NAME; and echo $ZELLIJ_SESSION_NAME
        return 0
    end

    for index in (seq 1 (count $argv))
        switch $argv[$index]
            case -s --session
                set -l next_index (math $index + 1)
                test $next_index -le (count $argv); and echo $argv[$next_index]; and return 0
        end
    end
    set -q ZELLIJ_SESSION_NAME; and echo $ZELLIJ_SESSION_NAME
end

function __kitty_context_preexec --on-event fish_preexec
    set -l tokens (string split -n ' ' -- (string trim -- $argv[1]))
    set -q tokens[1]; or return 0

    switch $tokens[1]
        case ssh mosh
            __kitty_context_set ssh (__ssh_context_host_from_args $tokens[2..-1]) "" "$tokens[1]"
        case kitten
            if test (count $tokens) -ge 2; and test "$tokens[2]" = ssh
                __kitty_context_set ksh (__ssh_context_host_from_args $tokens[3..-1]) "" "kitten ssh"
            else
                __kitty_context_set kitten "" "" "$tokens[2]"
            end
        case kitty
            if test (count $tokens) -ge 3; and test "$tokens[2]" = +kitten
                if test "$tokens[3]" = ssh
                    __kitty_context_set ksh (__ssh_context_host_from_args $tokens[4..-1]) "" "kitten ssh"
                else
                    __kitty_context_set kitten "" "" "$tokens[3]"
                end
            end
        case zellij
            __kitty_context_set zellij "" (__zellij_session_from_args $tokens[2..-1]) zellij
    end
end

__kitty_context_idle

if command -q kitten
    abbr -a ksh kitten ssh
    abbr -a kat kitten icat
end

function kctx --description "Show current Kitty context state"
    if test "$argv[1]" = --all
        set -l context_resolver ~/.config/kitty/context_state.py
        if not command -q kitten
            echo "kctx: kitten not found" >&2
            return 1
        end
        if not command -q python3
            echo "kctx: python3 not found" >&2
            return 1
        end
        if not test -e $context_resolver
            echo "kctx: context_state.py not found" >&2
            return 1
        end

        set -l kitty_ls (kitten @ ls 2>/dev/null | string collect)
        if test -z "$kitty_ls"
            echo "kctx: failed to query kitty windows" >&2
            return 1
        end

        printf "%s\n" $kitty_ls | python3 $context_resolver --jsonl | python3 -c '
import json
import sys

for line in sys.stdin:
    record = json.loads(line)
    resolved = record.get("resolved", {})
    marker = "◆" if record.get("is_current") else "●" if record.get("marker") == "*" else " "
    scope = "os{} t{} w{}".format(record.get("os_window_id", ""), record.get("tab_index", ""), record.get("window_id", ""))
    title = resolved.get("title", "")
    display_title = record.get("window_title") or record.get("tab_title") or ""
    print(f"{marker} {scope:<13} {title:<42} {display_title}")
'
        set -l pipe_status $pipestatus
        if test $pipe_status[1] -ne 0
            echo "kctx: kitten @ ls failed" >&2
            return 1
        end
        if test $pipe_status[2] -ne 0
            echo "kctx: context_state.py --jsonl failed" >&2
            return 1
        end
        return $pipe_status[3]
    end

    if not set -q KITTY_WINDOW_ID
        echo "kctx: not running inside kitty" >&2
        return 1
    end

    if not command -q kitten
        echo "kctx: kitten not found" >&2
        return 1
    end

    if not command -q jq
        echo "kctx: jq not found" >&2
        return 1
    end

    set -l kitty_ls (kitten @ ls 2>/dev/null | string collect)
    if test -z "$kitty_ls"
        echo "kctx: failed to query kitty windows" >&2
        return 1
    end

    set -l context_resolver ~/.config/kitty/context_state.py
    if command -q python3; and test -e $context_resolver
        printf "%s\n" $kitty_ls | python3 $context_resolver $KITTY_WINDOW_ID 2>/dev/null
    end

    printf "%s\n" $kitty_ls | jq -r --argjson window_id "$KITTY_WINDOW_ID" '
        def show_vars($vars; $keys):
          $keys[] as $key
          | select(($vars[$key] // "") != "")
          | "  \($key): \($vars[$key])";

        .[] as $os_window
        | $os_window.tabs[] as $tab
        | $tab.windows[]
        | select(.id == $window_id)
        | . as $window
        | ($window.user_vars // {}) as $vars
        | ($window.foreground_processes[-1] // {}) as $process
        | [
            "kitty:",
            "  os_window_id: \($os_window.id)",
            "  tab_id: \($tab.id)",
            "  tab_title: \($tab.title)",
            "  window_id: \($window.id)",
            "  window_title: \($window.title)",
            "process:",
            "  cwd: \($process.cwd // $window.cwd // "")",
            "  pid: \($process.pid // "")",
            "  cmdline: \(($process.cmdline // []) | join(" "))",
            "context:",
            (show_vars($vars; ["PROGRAM", "HOST", "CWD", "PROJECT", "SESSION", "COMMAND", "CTX_OWNER", "CTX_UPDATED_AT", "CTX_TTL"])),
            "agent:",
            (show_vars($vars; ["AGENT", "AGENT_STATE", "AGENT_MODEL", "AGENT_PROVIDER", "AGENT_SESSION", "AGENT_TASK", "AGENT_CONTEXT", "AGENT_COST", "AGENT_TOOL", "AGENT_SUBAGENT", "AGENT_OWNER", "AGENT_UPDATED_AT", "AGENT_TTL"])),
            "user_vars:",
            (($vars | to_entries[]? | "  \(.key): \(.value)"))
          ]
        | .[]
    '
end

function kls --description "Alias for kctx"
    kctx $argv
end

function text_work --description "Send text to kitty worker tag"
    set -l msg (string join " " -- $argv)
    kitten @ --to unix:/tmp/kitten send-text -m var:tag=worker "$msg"
end

function run_work --description "Run a command in kitty worker"
    if test (count $argv) -eq 0
        echo "run_work: missing command" >&2
        return 1
    end

    set -l parts
    for arg in $argv
        set -a parts (string escape -- $arg)
    end

    set -l cmd (string join " " -- $parts)

    text_work $cmd
    kitten @ --to unix:/tmp/kitten send-key -m var:tag=worker enter
end

function sh_work --description "Run raw shell command in kitty worker"
    if test (count $argv) -eq 0
        echo "sh_work: missing command string" >&2
        return 1
    end

    set -l cmd (string join " " -- $argv)

    text_work $cmd
    kitten @ --to unix:/tmp/kitten send-key -m var:tag=worker enter
end
