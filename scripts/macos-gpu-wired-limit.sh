#!/bin/sh
set -eu

LABEL="local.gpu-wired-limits"
PLIST="/Library/LaunchDaemons/${LABEL}.plist"
LOG="/var/log/${LABEL}.log"

die() {
    printf 'error: %s\n' "$1" >&2
    exit 1
}

require_macos_arm64() {
    [ "$(uname -s)" = Darwin ] || die "macOS only"
    [ "$(uname -m)" = arm64 ] || die "Apple Silicon only"
}

require_root() {
    [ "$(id -u)" -eq 0 ] || die "run with sudo: sudo $0 $1"
}

is_positive_int() {
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
        *) [ "$1" -gt 0 ] ;;
    esac
}

compute_limits() {
    mem_bytes=$(/usr/sbin/sysctl -n hw.memsize)
    mem_mb=$((mem_bytes / 1048576))

    if [ -z "${WIRED_LIMIT_MB:-}" ]; then
        [ "$mem_mb" -ge 65536 ] || die "RAM is ${mem_mb} MiB (< 64 GiB); pass WIRED_LIMIT_MB explicitly if intended"
        if [ "$mem_mb" -ge 524288 ]; then
            reserve_mb=$((mem_mb / 16))
        else
            reserve_mb=16384
        fi
        wired_limit_mb=$((mem_mb - reserve_mb))
    else
        wired_limit_mb=$WIRED_LIMIT_MB
    fi

    user_wire_limit=${USER_WIRE_LIMIT:-$((mem_bytes * 95 / 100))}

    is_positive_int "$wired_limit_mb" || die "invalid WIRED_LIMIT_MB: $wired_limit_mb"
    is_positive_int "$user_wire_limit" || die "invalid USER_WIRE_LIMIT: $user_wire_limit"
    [ "$wired_limit_mb" -lt "$mem_mb" ] || die "WIRED_LIMIT_MB ($wired_limit_mb) must be < total RAM (${mem_mb} MiB)"
    [ "$user_wire_limit" -lt "$mem_bytes" ] || die "USER_WIRE_LIMIT ($user_wire_limit) must be < total RAM ($mem_bytes)"
}

render_plist() {
    cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>${LABEL}</string>
	<key>ProgramArguments</key>
	<array>
		<string>/usr/sbin/sysctl</string>
		<string>-w</string>
		<string>iogpu.wired_limit_mb=${wired_limit_mb}</string>
		<string>vm.global_user_wire_limit=${user_wire_limit}</string>
		<string>vm.user_wire_limit=${user_wire_limit}</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
	<key>StandardOutPath</key>
	<string>${LOG}</string>
	<key>StandardErrorPath</key>
	<string>${LOG}</string>
</dict>
</plist>
EOF
}

cmd_status() {
    compute_limits
    printf 'Hardware RAM: %s bytes (%s GiB)\n' "$mem_bytes" "$((mem_mb / 1024))"
    printf '\nCurrent sysctl values:\n'
    for key in iogpu.wired_limit_mb vm.global_user_wire_limit vm.user_wire_limit; do
        val=$(/usr/sbin/sysctl -n "$key" 2>/dev/null || printf '(unavailable)')
        printf '  %s = %s\n' "$key" "$val"
    done
    printf '\nTarget values:\n'
    printf '  iogpu.wired_limit_mb = %s\n' "$wired_limit_mb"
    printf '  vm.global_user_wire_limit = %s\n' "$user_wire_limit"
    printf '  vm.user_wire_limit = %s\n' "$user_wire_limit"
    printf '\nLaunchDaemon:\n'
    if [ -f "$PLIST" ]; then
        printf '  plist: %s (installed)\n' "$PLIST"
    else
        printf '  plist: %s (not installed)\n' "$PLIST"
    fi
    if /bin/launchctl print "system/${LABEL}" >/dev/null 2>&1; then
        printf '  state: loaded (system/%s)\n' "$LABEL"
    else
        printf '  state: not loaded\n'
    fi
}

cmd_print() {
    compute_limits
    render_plist
}

cmd_install() {
    require_root install
    compute_limits

    tmp=$(/usr/bin/mktemp "/Library/LaunchDaemons/.${LABEL}.XXXXXX")
    trap 'rm -f "$tmp"' EXIT INT TERM
    render_plist >"$tmp"
    /usr/bin/plutil -lint "$tmp" >/dev/null
    /usr/sbin/chown root:wheel "$tmp"
    /bin/chmod 644 "$tmp"
    /bin/mv "$tmp" "$PLIST"
    trap - EXIT INT TERM

    /usr/sbin/sysctl -w \
        "iogpu.wired_limit_mb=${wired_limit_mb}" \
        "vm.global_user_wire_limit=${user_wire_limit}" \
        "vm.user_wire_limit=${user_wire_limit}"

    /bin/launchctl bootout "system/${LABEL}" 2>/dev/null || true
    /bin/launchctl bootstrap system "$PLIST"

    printf '\nInstalled %s.\n' "$PLIST"
    printf 'Restart MLX services (e.g. `darkbloom restart`) so they read the new limits.\n'
}

cmd_uninstall() {
    require_root uninstall
    /bin/launchctl bootout "system/${LABEL}" 2>/dev/null || true
    /bin/rm -f "$PLIST" "$LOG"
    /usr/sbin/sysctl -w iogpu.wired_limit_mb=0
    printf 'Removed %s and reset iogpu.wired_limit_mb=0.\n' "$PLIST"
    printf 'vm.global_user_wire_limit and vm.user_wire_limit will return to macOS defaults on next reboot.\n'
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [status|print|install|uninstall]

Manage a standalone LaunchDaemon (${LABEL}) for macOS GPU wired-memory sysctl limits.

Commands:
  status     Show current sysctl values, computed targets, and daemon state (default)
  print      Print the generated LaunchDaemon plist XML without modifying the system
  install    Apply sysctl limits now and install ${PLIST} (requires sudo)
  uninstall  Remove ${PLIST} and reset iogpu.wired_limit_mb=0 (requires sudo)

Optional environment overrides:
  WIRED_LIMIT_MB   Override iogpu.wired_limit_mb (default: total RAM minus 16 GiB)
  USER_WIRE_LIMIT  Override vm.*_user_wire_limit in bytes (default: 95% of RAM)
EOF
}

require_macos_arm64

case "${1:-status}" in
    status) cmd_status ;;
    print) cmd_print ;;
    install) cmd_install ;;
    uninstall) cmd_uninstall ;;
    -h|--help|help) usage ;;
    *) usage >&2; exit 2 ;;
esac
